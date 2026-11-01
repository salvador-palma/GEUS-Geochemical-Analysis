
import matplotlib.pyplot as plt
import pandas as pd
from joblib import Parallel, delayed
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from xgboost import XGBRegressor

from GreenlandUtils import Split, Printable
import numpy as np


def AggregateFolds(kfoldResults: dict):
    aggregated = {}

    for element, folds in kfoldResults.items():
        valid = [s for s in folds.values() if s["r2"] is not None and not np.isnan(s["r2"])]
        if not valid:
            aggregated[element] = { "r2": None, "mae": None }
            continue

        aggregated[element] = {
            "r2": float(np.mean([s["r2"] for s in valid])),
            "r2_std": float(np.std([s["r2"] for s in valid])),
            "mae": float(np.mean([s["mae"] for s in valid])),
            "y_pred": np.concatenate([s["y_pred"] for s in valid]),
            "y_test": np.concatenate([s["y_test"] for s in valid]),
        }

    return aggregated

def ArrangeData(df: pd.DataFrame, element: str, elementCols: list[str]):
    df = df.copy()
    df = df.dropna(subset=[element])
    X = df[elementCols].copy()
    y = df[element].copy()
    X = X.drop(columns=[element], errors='ignore')

    return X, y

def DropDegenerateColumns(X_train: pd.DataFrame, X_test: pd.DataFrame):
    #A KNN column can end up constant or near-empty on a given fold even when its
    #source element is fine, which is the one input HistGradientBoosting cannot bin
    usable = [col for col in X_train.columns if X_train[col].nunique(dropna=True) >= 2]

    return X_train[usable], X_test[usable]

def MakeModel(modelType: str="hgb", n_jobs: int=-1, estimators: int=200):
    #HistGradientBoosting threads internally and takes no n_jobs
    if modelType == "rf":
        return RandomForestRegressor(n_estimators=estimators, random_state=42, n_jobs=n_jobs)
    if modelType == "xgb":
        #Like HGB, XGBoost splits on NaN directly, so the missing element cells need no imputing.
        #n_jobs is passed through because the outer joblib loop already owns the cores
        return XGBRegressor(n_estimators=estimators, random_state=42, n_jobs=n_jobs,
                            tree_method="hist", learning_rate=0.1, max_depth=6)
    return HistGradientBoostingRegressor(max_iter=estimators, random_state=42)

def TrainRandomForest(df_train: pd.DataFrame, df_test: pd.DataFrame, element: str, elementCols: list[str], n_jobs:int=-1, estimators:int=200, modelType:str="hgb"):
    X_train, y_train = ArrangeData(df_train, element, elementCols)
    X_test, y_test = ArrangeData(df_test, element, elementCols)

    if X_train.empty or X_test.empty:
        return { "r2": None, "mae": None }

    X_train, X_test = DropDegenerateColumns(X_train, X_test)
    if X_train.empty:
        return { "r2": None, "mae": None }

    model = MakeModel(modelType, n_jobs=n_jobs, estimators=estimators)
    model.fit(X_train, y_train)

    r2 = model.score(X_test, y_test)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)

    return { "r2": r2, "mae": mae, "y_pred": y_pred, "y_test": y_test }


def TrainAllElements(split: Split, elementsToTrain: list[str], elementCols: list[str]=None, n_jobs: int=-1, modelType: str="hgb", **kwargs):

    train, test = split.data["train"], split.data["test"]

    scores = Parallel(n_jobs=n_jobs)(
        delayed(TrainRandomForest)(train, test, element, elementCols, n_jobs=1, modelType=modelType)
        for element in elementsToTrain
    )

    return dict(zip(elementsToTrain, scores))

def TrainAllElementsKFold(kfold_splits: list[Split], elementsToTrain: list[str], elementCols: list[str]=None, n_jobs: int=-1, modelType: str="hgb", **kwargs):

    jobs = [
        (element, foldIdx, split)
        for element in elementsToTrain
        for foldIdx, split in enumerate(kfold_splits)
    ]

    scores = Parallel(n_jobs=n_jobs)(
        delayed(TrainRandomForest)(
            split.data["train"], split.data["test"], element, elementCols, n_jobs=1, modelType=modelType
        )
        for element, foldIdx, split in jobs
    )

    results = {element: {} for element in elementsToTrain}
    for (element, foldIdx, _), score in zip(jobs, scores):
        results[element][foldIdx] = score

    return results


def PooledR2Log(results: dict):
    ss_res, ss_tot = 0.0, 0.0

    for score in results.values():
        if score["r2"] is None or "y_test" not in score:
            continue

        y_test = np.asarray(score["y_test"], dtype=float)
        y_pred = np.asarray(score["y_pred"], dtype=float)

        #Log10 scale so wt%/ppm/ppb elements contribute comparably (drop BDL zeros)
        valid = (y_test > 0) & (y_pred > 0)
        if valid.sum() < 2:
            continue

        y_test_log = y_test[valid]
        y_pred_log = y_pred[valid]

        ss_res += ((y_test_log - y_pred_log) ** 2).sum()
        ss_tot += ((y_test_log - y_test_log.mean()) ** 2).sum()

    return 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

def GlobalScores(printable: Printable, results: dict):
    valid_r2 = [s["r2"] for s in results.values() if s["r2"] is not None and not np.isnan(s["r2"])]

    printable.add("Mean R2 Score", f"{np.mean(valid_r2):.4f}")
    printable.add("Median R2 Score", f"{np.median(valid_r2):.4f}")
    printable.add("Pooled R2 Score (log10)", f"{PooledR2Log(results):.4f}")

def ReportResults(results: dict, title: str = "Element Scores"):
    printable = Printable()
    printable.title(title)
    for element, score in results.items():
        if score["r2"] is None:
            continue

        r2 = f"R2: {score['r2']:>8.4f}"
        #r2_std only exists for k-fold results, so pad single-split rows to match
        if "r2_std" in score:
            r2 += f" ± {score['r2_std']:.4f}"
        else:
            r2 += " " * 9

        printable.add(element, f"{r2}   MAE: {score['mae']:.4f}")

    printable.rest()
    printable.title("Global Score")

    GlobalScores(printable, results)

    printable.pretty()
    
def CompareVariantsOnGraph(allResults: dict[str, dict], elements: list[str], metric="r2", title="Comparison of KNN Variants"):
    names = list(allResults.keys())
    x = np.arange(len(elements))
    width = 0.8 / len(names)

    fig, ax = plt.subplots(figsize=(16, 8))

    for i, name in enumerate(names):
        values = [allResults[name][element][metric] or 0 for element in elements]
        offset = (i - (len(names) - 1) / 2) * width
        ax.bar(x + offset, values, width, label=name)

    ax.set_xlabel("Element")
    ax.set_ylabel(metric.upper())
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(elements, rotation=90)
    ax.set_ylim(0, 1)
    ax.legend()

    plt.tight_layout()
    plt.show()
