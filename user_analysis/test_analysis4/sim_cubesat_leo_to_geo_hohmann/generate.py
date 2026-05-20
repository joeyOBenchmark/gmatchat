#!/usr/bin/env python3
"""
CubeSat LEO to GEO Hohmann Transfer

Mission: 32 kg CubeSat (12U-class) transfers from a 500 km circular LEO
         to GEO (35786 km altitude) using a 2-burn chemical Hohmann transfer.

Strategy:
  Burn 1 (perigee): impulsive burn at LEO perigee raises apogee to GEO altitude.
  Burn 2 (apogee):  impulsive burn at GEO apogee circularises the orbit.

No inclination change is included -- the spacecraft ends in a 28.5 deg GTO/GEO.
A dedicated plane-change maneuver would be needed to reach true operational GEO
(0 deg inclination); that burns ~1.7 km/s extra and is out of scope here.

Mass budget:
  Dry mass         : 10 kg
  Chemical propellant: 22 kg
  Wet mass         : 32 kg

Propulsion:
  Thrust           : 5 N  (green-propellant thruster, e.g. Bradford ECAPS HPGP)
  Isp              : 350 s

Estimated delta-V (impulsive):
  Burn 1 (perigee raise)  : ~2.37 km/s
  Burn 2 (apogee circul.) : ~1.44 km/s
  Total                   : ~3.81 km/s

Propellant margin at 350 s Isp: ~200 m/s reserve
"""

import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, '/gmatbard')

from gmatbard.high_level import SimBuilder, Starship, MissionSequenceBuilder
from gmatbard.low_level.result_parsers import ResultParser

EARTH_RADIUS_KM = 6378.137
LEO_ALT_KM      = 500.0
GEO_ALT_KM      = 35786.033
GEO_RADIUS_KM   = EARTH_RADIUS_KM + GEO_ALT_KM   # 42164.170 km

SIM_DIR     = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(SIM_DIR, 'mission.script')
BURN_CSV    = os.path.join(SIM_DIR, 'CubeSat_BurnReport.csv')
OEM_PATH    = os.path.join(SIM_DIR, 'CubeSat_Ephemeris.oem')
OEM_DAT     = OEM_PATH + '.dat'
PLOTS_DIR   = os.path.join(SIM_DIR, 'plots')


def build_mission():
    sim = SimBuilder(
        name="CubeSat_Hohmann",
        bodies=["Earth"],
        enable_visualizations=True,
        propagator_type="RungeKutta89",
        enable_drag=False,
        enable_srp=False
    )

    # Write DC report inside sim dir
    sim.diff_corrector.properties["ReportFile"] = os.path.join(SIM_DIR, 'dc_report.data')

    vehicle = Starship(
        sim,
        name="CubeSat",
        epoch="01 Jan 2025 12:00:00.000",
        sma=EARTH_RADIUS_KM + LEO_ALT_KM,   # 6878.137 km
        ecc=0.0,
        inc=28.5,
        raan=0.0,
        aop=0.0,
        ta=0.0,
        dry_mass_kg=10.0,
        chemical_fuel_kg=22.0,
        chemical_thrust_N=5.0,
        chemical_isp_s=350.0
    )

    msb = MissionSequenceBuilder(
        sim.script,
        vehicle.spacecraft,
        sim.propagator_name,
        solver_name=sim.solver_name,
        burn_report_filename=BURN_CSV,
        ephemeris_filename=OEM_PATH,
        ephemeris_step_size_s=300.0
    )

    msb.coast(days=0.05)
    msb.report_state("LEO Initial State (500 km circular)")

    # 2-burn Hohmann: LEO -> GEO
    msb.add(vehicle.propulsion.chem1.maneuvers.hohmann_transfer(
        target_radius=GEO_RADIUS_KM,
        ecc=0.0,
        pre_burn_description="Hohmann Burn 1 - LEO perigee raise to GTO"
    ))

    msb.coast(days=0.5)
    msb.report_state("GEO Final State (35786 km circular)")

    msb.finalize("CubeSat Hohmann LEO to GEO complete")

    script_path = sim.generate(SCRIPT_PATH)
    print(f"[OK] Generated: {script_path}")
    return sim, script_path


def run_and_parse(sim, script_path):
    print("\nRunning GMAT ...")
    results = sim.run()
    print(f"[OK] GMAT return code: {results['returncode']}")

    if results['returncode'] != 0:
        print("GMAT FAILED")
        print(results.get('stderr', '')[:3000])
        return None

    parser = ResultParser()
    report_data = parser.parse_report_files(script_path, sim.script.reports)
    results['report_files'] = report_data
    return results


def write_results_csv(results):
    """Read BurnReport CSV directly and write results.csv."""
    import math

    if not os.path.exists(BURN_CSV):
        print(f"[WARN] Burn CSV not found: {BURN_CSV}")
        return

    # The BurnReport CSV has quoted multi-line headers; read with quotechar
    try:
        df_raw = pd.read_csv(BURN_CSV, quotechar='"')
    except Exception as e:
        print(f"[WARN] Could not read burn CSV: {e}")
        return

    # Strip whitespace from column names
    df_raw.columns = [c.strip() for c in df_raw.columns]

    # Keep only impulse rows (actual burns, not state reports)
    df_burns = df_raw[df_raw['burn_type'] == 'impulse'].copy().reset_index(drop=True)

    if df_burns.empty:
        print("[WARN] No impulse burns found in report")
        return

    rows = []
    for i, row in df_burns.iterrows():
        rows.append({
            'burn_number':         i + 1,
            'description':         str(row.get('burn_description', f'Burn {i+1}')).strip(),
            'elapsed_days':        round(float(row.get('CubeSat.ElapsedDays', 0)), 4),
            'mass_before_kg':      round(float(row.get('mass_prior_to_burn', 0)), 3),
            'propellant_used_kg':  round(float(row.get('propused_kg', 0)), 3),
            'mass_after_kg':       round(float(row.get('CubeSat.TotalMass', 0)), 3),
            'delta_v_m_s':         round(float(row.get('mag_burn_kmps', 0)) * 1000.0, 2),
            'sma_km':              round(float(row.get('CubeSat.Earth.SMA', 0)), 3),
            'ecc':                 round(float(row.get('CubeSat.Earth.ECC', 0)), 6),
            'inc_deg':             round(float(row.get('CubeSat.EarthMJ2000Eq.INC', 0)), 4),
        })

    df_out = pd.DataFrame(rows)
    total_prop = df_out['propellant_used_kg'].sum()
    total_dv   = df_out['delta_v_m_s'].sum()
    transfer_days = df_out['elapsed_days'].max()

    # Verify with Tsiolkovsky
    m0 = rows[0]['mass_before_kg']
    mf = rows[-1]['mass_after_kg']
    dv_tsiol = 350.0 * 9.80665 * math.log(m0 / mf)

    summary = pd.DataFrame([{
        'burn_number':        'TOTAL',
        'description':        'Mission summary',
        'elapsed_days':       round(transfer_days, 4),
        'mass_before_kg':     rows[0]['mass_before_kg'],
        'propellant_used_kg': round(total_prop, 3),
        'mass_after_kg':      rows[-1]['mass_after_kg'],
        'delta_v_m_s':        round(total_dv, 2),
        'sma_km':             rows[-1]['sma_km'],
        'ecc':                rows[-1]['ecc'],
        'inc_deg':            rows[-1]['inc_deg'],
    }])

    out_path = os.path.join(SIM_DIR, 'results.csv')
    pd.concat([df_out, summary], ignore_index=True).to_csv(out_path, index=False)
    print(f"[OK] results.csv written: {out_path}")
    print(f"\n  Total propellant : {total_prop:.2f} kg")
    print(f"  Total dV         : {total_dv:.0f} m/s")
    print(f"  Tsiolkovsky dV   : {dv_tsiol:.0f} m/s")
    print(f"  Transfer time    : {transfer_days:.4f} days")
    print(f"  Final SMA        : {rows[-1]['sma_km']:.1f} km")


def generate_plots(results):
    """Generate all standard plots."""
    os.makedirs(PLOTS_DIR, exist_ok=True)

    # ---- BurnReportPlotter ----
    if os.path.exists(BURN_CSV):
        try:
            from gmatbard.visualization import BurnReportPlotter
            from bokeh.io import save
            from bokeh.resources import CDN

            bp = BurnReportPlotter(BURN_CSV)

            fig = bp.plot_summary_mpl()
            fig.savefig(os.path.join(PLOTS_DIR, 'burn_summary.png'), dpi=150, bbox_inches='tight')
            plt.close(fig)

            fig = bp.plot_dv_mpl()
            fig.savefig(os.path.join(PLOTS_DIR, 'delta_v.png'), dpi=150, bbox_inches='tight')
            plt.close(fig)

            fig = bp.plot_mass_mpl()
            fig.savefig(os.path.join(PLOTS_DIR, 'mass_history.png'), dpi=150, bbox_inches='tight')
            plt.close(fig)

            save(bp.plot_summary_bokeh(),
                 filename=os.path.join(PLOTS_DIR, 'burn_summary.html'),
                 resources=CDN, title='Burn Summary')

            print("[OK] Burn report plots saved")
        except Exception as e:
            print(f"[WARN] BurnReportPlotter failed: {e}")
    else:
        print(f"[WARN] Burn CSV not found: {BURN_CSV}")

    # ---- EphemerisPlotter (.oem.dat) ----
    if os.path.exists(OEM_DAT):
        try:
            from gmatbard.visualization import EphemerisPlotter
            from bokeh.io import save
            from bokeh.resources import CDN

            ep = EphemerisPlotter(OEM_DAT)

            fig = ep.plot_summary_mpl()
            fig.savefig(os.path.join(PLOTS_DIR, 'ephemeris_summary.png'), dpi=150, bbox_inches='tight')
            plt.close(fig)

            save(ep.plot_summary_bokeh(),
                 filename=os.path.join(PLOTS_DIR, 'ephemeris.html'),
                 resources=CDN, title='Ephemeris')

            print("[OK] Ephemeris plots saved")
        except Exception as e:
            print(f"[WARN] EphemerisPlotter failed: {e}")
    else:
        print(f"[WARN] OEM .dat file not found: {OEM_DAT}")

    # ---- TrajectoryPlotter (.oem) ----
    if os.path.exists(OEM_PATH):
        try:
            from gmatbard.visualization import TrajectoryPlotter
            from bokeh.io import save
            from bokeh.resources import CDN
            import plotly.io as pio

            tp = TrajectoryPlotter(OEM_PATH)

            fig = tp.plot_trajectory_mpl()
            fig.savefig(os.path.join(PLOTS_DIR, 'trajectory_3d.png'), dpi=150, bbox_inches='tight')
            plt.close(fig)

            pio.write_html(tp.plot_trajectory_plotly(),
                           file=os.path.join(PLOTS_DIR, 'trajectory_3d.html'),
                           auto_open=False)

            save(tp.plot_trajectory_bokeh(),
                 filename=os.path.join(PLOTS_DIR, 'trajectory_2d.html'),
                 resources=CDN, title='Trajectory')

            print("[OK] Trajectory plots saved")
        except Exception as e:
            print(f"[WARN] TrajectoryPlotter failed: {e}")
    else:
        print(f"[WARN] OEM file not found: {OEM_PATH}")


def main():
    print("=" * 65)
    print("CubeSat Hohmann LEO -> GEO Transfer")
    print("=" * 65)

    sim, script_path = build_mission()
    results = run_and_parse(sim, script_path)

    if results:
        write_results_csv(results)
        generate_plots(results)
    else:
        print("[ERROR] Simulation failed -- check GMAT output log")


if __name__ == "__main__":
    main()
