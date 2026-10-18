"""Entry point for this focused manuscript release; no online publication."""
from pathlib import Path
import argparse,subprocess,sys

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--raw',type=Path,required=True);ap.add_argument('--rain',type=Path);ap.add_argument('--rebuild-panel',action='store_true');ap.add_argument('--manuscript',type=Path)
    a=ap.parse_args();code=Path(__file__).resolve().parent
    def run(name,*args):subprocess.run([sys.executable,str(code/name),*map(str,args)],check=True)
    if a.rebuild_panel:
        if a.rain is None:ap.error('--rain is required with --rebuild-panel')
        run('Build_MODIS_Rainfall_Panel.py','--raw',a.raw,'--rain',a.rain,'--output',a.output)
    run('Analyse_Rainfall_Conditional_Logistic.py','--output',a.output)
    run('Make_Table_S10_Rainfall_Category_Counts.py','--output',a.output)
    run('Analyse_Working_Poisson_Sensitivity.py','--output',a.output)
    run('Analyse_Burned_Area_2023.py','--raw',a.raw,'--output',a.output)
    run('Make_Figure_1_Peatland_Map_Coverage.py','--raw',a.raw,'--output',a.output)
    run('Make_Figures_and_Sensor_Tables.py','--raw',a.raw,'--output',a.output)
    run('Make_Graphical_Abstract.py','--output',a.output)
    run('Make_Supplementary_Additions_S1_S10.py','--output',a.output)
    if a.manuscript:run('Update_Manuscript.py','--input',a.manuscript,'--output',a.output)
    run('Validate_Consistency.py','--output',a.output)

if __name__=='__main__':main()
