import pandas as pd
import psp.AmorphousBuilder as ab

input_df = pd.read_csv("input_PE.csv", low_memory=False)
amor = ab.Builder(
    input_df,
    ID_col="ID",
    SMILES_col="smiles",
    OutDir='amorphous_models',
    Length='Len',
    NumConf='NumConf',
    LeftCap = "LeftCap",
    RightCap = "RightCap",
    Loop='Loop',
    density=0.65,
    box_type='c',
    BondInfo=False
    #box_size=[0.0,20,0.0,20,0.0,20]
)
amor.Build()
