
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm
from tqdm import tqdm
from dataclasses import dataclass

@dataclass
class Split:
    data : dict[str, pd.DataFrame]

BASEMAP_PATH = Path("Data/GreenlandMapPlain.png")
BASEMAP_BBOX = (-400_000.0, 6_500_000.0, 1_200_000.0, 9_400_000.0)

PRIMARY, SECONDARY, MUTED, SURFACE, SPINE = "#0b0b0b", "#52514e", "#898781", "#fcfcfb", "#c3c2b7"



def lonlatToUTM24N(lon, lat) -> tuple[np.ndarray, np.ndarray]:
 
    lon, lat = np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)
    lon0, k0, a, e2 = -39.0, 0.9996, 6378137.0, 0.00669438

    lat_r = np.radians(lat)
    dlon = np.radians(((lon - lon0 + 180.0) % 360.0) - 180.0)
    sin_lat, cos_lat = np.sin(lat_r), np.cos(lat_r)
    n = a / np.sqrt(1 - e2 * sin_lat ** 2)
    t = np.tan(lat_r) ** 2
    c = e2 / (1 - e2) * cos_lat ** 2
    aa = dlon * cos_lat
    m = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64) * lat_r - (3 * e2 / 8 + 3 * e2 ** 2 / 32) * np.sin(2 * lat_r) + (15 * e2 ** 2 / 256) * np.sin(4 * lat_r))
    x = k0 * n * (aa + (1 - t + c) * aa ** 3 / 6) + 500000
    y = k0 * (m + n * sin_lat / cos_lat * (aa ** 2 / 2 + (5 - t + 9 * c) * aa ** 4 / 24))
    return x, y


def PlotSamplesOnMap(df: pd.DataFrame, element: str = None, title: str = None, lonCol: str = "Longitude", latCol: str = "Latitude", colorCol: str = "colors", zoomToData: bool = True, pointSize: float = 6, basemap: Path = None, ax=None, dotColor: str = "#2a78d6", cmap: str = "viridis", **kwargs):
    
    basemap = Path(basemap) if basemap is not None else BASEMAP_PATH

    lon = pd.to_numeric(df[lonCol], errors="coerce")
    lat = pd.to_numeric(df[latCol], errors="coerce")
    valid = lon.notna() & lat.notna()

    #Check valid element values
    values = None
    if element is not None:
        values = pd.to_numeric(df[element], errors="coerce")
        valid &= values.notna() & (values > 0)

    #Per-point colors, only when not colouring by element value
    colors = None
    if values is None and colorCol in df.columns:
        colors = df[colorCol]
        valid &= colors.notna()

    #Filter valid coordinates and values (if applicable)
    lon, lat = lon[valid], lat[valid]
    if values is not None:
        values = values[valid]
    if colors is not None:
        colors = colors[valid]

    if len(lon) == 0:
        raise ValueError(f"No samples with usable coordinates{f' and {element}' if element else ''}")


    x, y = lonlatToUTM24N(lon.to_numpy(), lat.to_numpy())

    if ax is None:
        _, ax = plt.subplots(figsize=(7, 9))
    ax.set_facecolor(SURFACE)


    minx, miny, maxx, maxy = BASEMAP_BBOX
    ax.imshow(plt.imread(basemap), extent=(minx, maxx, miny, maxy), origin="upper", interpolation="bilinear", zorder=0)


    if values is None:
        ax.scatter(x, y, s=pointSize, c=colors.to_numpy() if colors is not None else dotColor, alpha=0.7, linewidths=0, zorder=2)
    else:
        sc = ax.scatter(x, y, s=pointSize, c=values.to_numpy(), cmap=cmap, norm=LogNorm(), alpha=0.9, linewidths=0.2, edgecolors=SURFACE, zorder=2)
        cb = plt.colorbar(sc, ax=ax, fraction=0.035, pad=0.02)
        cb.set_label(element, color=SECONDARY, fontsize=9)
        cb.ax.tick_params(labelsize=8, colors=MUTED)
        cb.outline.set_visible(False)

    #Zoom to min content or show whole Greenland
    if zoomToData:
        ax.set_xlim(x.min() - 150_000.0, x.max() + 150_000.0)
        ax.set_ylim(y.min() - 150_000.0, y.max() + 150_000.0)
    else:
        minx, miny, maxx, maxy = BASEMAP_BBOX
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        
    #Kwargs for color labels
    colorLabels = kwargs.get("colorLabels", None)
    if colorLabels is not None:
        for label, color in colorLabels.items():
            ax.scatter([], [], c=color, label=label, s=pointSize, alpha=0.7)
            
        ax.legend(loc="upper right", fontsize=8, frameon=False)

    ax.set_aspect("equal")
    if title is None:
        title = f"Sample locations - {element}" if element else "Sample locations"
    ax.set_title(f"{title}  ({len(x):,} samples)", color=PRIMARY, fontsize=12, pad=10, loc="left")
    ax.set_xlabel("Longitude (EPSG:32624)", color=MUTED, fontsize=8)
    ax.set_ylabel("Latitude (EPSG:32624)", color=MUTED, fontsize=8)
    ax.tick_params(colors=MUTED, labelsize=8)
    
    for spine in ax.spines.values():
        spine.set_color(SPINE)
    return ax

def MostCommonElements(df: pd.DataFrame, elementCols: list[str], top_n: int=10) -> list[tuple[str, int]]:
    
    elements = []
    for element in tqdm(elementCols, desc="Analyzing Elements"):
        usable = df[element].notna().sum()
        elements.append((element, usable))
        
    elements.sort(key=lambda x: x[1], reverse=True)
    
    return elements[:top_n]

def displaySplit(split: dict[str, pd.DataFrame], colors: list[str] = ["#ff0000", "#00ff00", "#0000ff"], title="Train-Val-Test Split"):
    
    split["train"]["colors"] = "#ff0000"
    split["val"]["colors"] = "#00ff00"
    split["test"]["colors"] = "#0000ff"

    merged = pd.concat([split["train"], split["val"], split["test"]])
        
    colorLabels = {"Train": colors[0], "Validation": colors[1], "Test": colors[2]}

    PlotSamplesOnMap(merged, colorCol="colors", title=title, colorLabels=colorLabels)
   
def verifyStratification(split: dict[str, pd.DataFrame], element: str):
    total = len(split["train"]) + len(split["val"]) + len(split["test"])
    train_ratio = len(split["train"]) / total
    val_ratio = len(split["val"]) / total
    test_ratio = len(split["test"]) / total
    
    train_element = len(split["train"][split["train"][element] > 0]) / total
    val_element = len(split["val"][split["val"][element] > 0]) / total
    test_element = len(split["test"][split["test"][element] > 0]) / total
    
    train_mean = split["train"][element].mean()
    val_mean = split["val"][element].mean()
    test_mean = split["test"][element].mean()
    
    printable = Printable()
    printable.title(f"Stratification Verification for {element}" if element is not None else "Stratification Verification")
    
    printable.add("Total Samples", total)
    printable.add("Train Ratio", f"{train_ratio:.2f} ({train_element:.2f}), Mean: {train_mean:.2f}")
    printable.add("Validation Ratio", f"{val_ratio:.2f} ({val_element:.2f}), Mean: {val_mean:.2f}")
    printable.add("Test Ratio", f"{test_ratio:.2f} ({test_element:.2f}), Mean: {test_mean:.2f}")
    printable.rest()
    printable.pretty()
    
def DFStats(df : pd.DataFrame, metaCols : list[str], n: int = 10) -> None:
    stats = Printable()
    stats.title("Quantities")
    stats.add("Rows", len(df))
    stats.add("Samples", len(df["Sample number"].unique()))
    stats.rest()
    
    stats.title("Structure")
    stats.add("Columns", len(df.columns))
    stats.add("Column Names", list(df.columns))
    stats.add("Meta Columns", len([col for col in df.columns if col in metaCols]))
    stats.add("Element Columns", len([col for col in df.columns if col not in metaCols]))
    stats.add("Columns lacking coordinates", len([1 for i in range(len(df)) if pd.isna(df["Longitude"][i]) or pd.isna(df["Latitude"][i])]))
    stats.rest()
    
    stats.title("Elements")
    
    elements = []
    for element in tqdm([col for col in df.columns if col not in metaCols], desc="Analyzing Elements"):
        usable = df[element].notna().sum()
        bdl = df[element].lt(0).sum()
        elements.append((element, usable, bdl))
        
    elements.sort(key=lambda x: x[1], reverse=True)
    stats.add("Top 10 Elements", [element for element, _, _ in elements[:10]])
    stats.rest()
    for element, usable, bdl in elements[:n]:
        stats.add(element, f"{usable} ({usable/len(df)*100:.2f}%), BDL: {bdl} ({bdl/len(df)*100:.2f}%)")
        
    stats.rest()    
    stats.pretty()

class Printable:
    content : list[tuple[str,any]]
    
    def __init__(self):
        self.content = []
    
    def __iter__(self):
        return self.content.__iter__()
        
    def pretty(self, minSeparation = 3, maxClamp = 30):
        maxTitleLength = max(len(title) for title, _ in self)
        maxValueLength = max(len(str(val)) for _, val in self)
        
        for title, result in self:
            if title == "":
                print("\n")
            elif title == "TitleFlag":
                sepNumb = (maxTitleLength + maxValueLength + minSeparation - len(str(result)) - 1) // 2
                sepNumb = min(sepNumb, maxClamp)
                print(f"{'='*sepNumb} {result} {'='*sepNumb}")
            else:
                print(f"{title}:{' '*(maxTitleLength-len(title) + minSeparation)}{result}")
    
    def add(self, title:str, value:any):
        self.content.append([title,value])
    
        
    def clear(self):
        self.content = []
        
    def flush(self):
        self.pretty()
        self.clear()
        
    def rest(self):
        self.content.append(["",""])
    
    def title(self, title):
        self.content.append(["TitleFlag", title])
        