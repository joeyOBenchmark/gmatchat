#!/usr/bin/env python3
"""
LEO to GEO Transfer using Electric Propulsion (EP Spiral Raise)

Mission: 200 kg spacecraft spirals from a 500 km circular LEO to GEO (35786 km)
         using a Hall-effect thruster (200 mN / 1800 s Isp).

Strategy: progressive_spiral_raise handles the large altitude change (~35286 km)
          in three staged passes (coarse -> medium -> fine).
          Inclination is not corrected here; a dedicated plane-change maneuver
          would be needed to achieve true operational GEO at 0 deg.

Mass budget:
  Dry mass  : 110 kg
  EP fuel   :  90 kg
  Wet mass  : 200 kg

Thruster:
  Thrust    : 0.2 N  (200 mN Hall-effect thruster)
  Isp       : 1800 s
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
GEO_ALT_KM      = 35786.0

SIM_DIR     = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(SIM_DIR, 'mission.script')
BURN_CSV    = os.path.join(SIM_DIR, 'Sat_BurnReport.csv')
OEM_PATH    = os.path.join(SIM_DIR, 'Sat_Ephemeris.oem')
OEM_DAT     = OEM_PATH + '.dat'
PLOTS_DIR   = os.path.join(SIM_DIR, 'plots')


def build_mission():
    sim = SimBuilder(
        name="LEO_GEO_EP",
        bodies=["Earth"],
        enable_visualizations=True,
        propagator_type="RungeKutta89",
        enable_drag=True,
        enable_srp=True
    )

    # Write DC solver report to sim dir to avoid ../output/ path issues
    sim.diff_corrector.properties["ReportFile"] = os.path.join(SIM_DIR, 'dc_report.data')

    vehicle = Starship(
        sim,
        name="Sat",
        epoch="01 Jan 2025 12:00:00.000",
        sma=EARTH_RADIUS_KM + LEO_ALT_KM,
        ecc=0.0,
        inc=28.5,
        raan=0.0,
        aop=0.0,
        ta=0.0,
        dry_mass_kg=110.0,
        ep_fuel_kg=90.0,
        ep_thrust_N=0.2,
        ep_isp_s=1800.0
    )

    msb = MissionSequenceBuilder(
        sim.script,
        vehicle.spacecraft,
        sim.propagator_name,
        solver_name=sim.solver_name,
        optimizer_name=sim.optimizer_name,
        burn_report_filename=BURN_CSV,
        ephemeris_filename=OEM_PATH,
        ephemeris_step_size_s=300.0
    )

    msb.coast(days=0.1)
    msb.report_state("Initial LEO 500km")

    msb.add(vehicle.propulsion.ep1.maneuvers.progressive_spiral_raise(
        target_radius=EARTH_RADIUS_KM + GEO_ALT_KM,
        pre_burn_description="EP Spiral LEO to GEO"
    ))

    msb.coast(days=0.5)
    msb.report_state("Final GEO orbit")
    msb.finalize("Mission Complete LEO to GEO EP")

    sim.generate(SCRIPT_PATH)
    print(f"[OK] Generated: {SCRIPT_PATH}")
    return sim


def run_and_parse(sim):
    print("Running GMAT...")
    results = sim.run()
    if results.get('returncode', 1) != 0:
        print("GMAT failed:")
        print(results.get('stderr', '')[:3000])
        return False
    print("[OK] GMAT run completed.")
    return True


def write_results_csv():
    """Read Sat_BurnReport.csv directly and write a tidy results.csv."""
    if not os.path.exists(BURN_CSV):
        print("[WARN] BurnReport CSV not found; skipping results.csv")
        return

    df = pd.read_csv(BURN_CSV)

    # Normalise duration column name
    for col in list(df.columns):
        if col.startswith('duration_s') and col != 'duration_s':
            df = df.rename(columns={col: 'duration_s'})
            break

    # Identify spacecraft prefix from column names
    sc = next((c.split('.')[0] for c in df.columns if c.endswith('.ElapsedDays')), 'Sat')

    initial = df.iloc[0]
    final   = df.iloc[-1]

    mass_i         = float(initial.get(f'{sc}.TotalMass', 0))
    mass_f         = float(final.get(f'{sc}.TotalMass', 0))
    prop_consumed  = mass_i - mass_f
    transfer_days  = float(final.get(f'{sc}.ElapsedDays', 0)) - float(initial.get(f'{sc}.ElapsedDays', 0))
    total_dv_km_s  = float(df.loc[df['burn_type'] == 'finite', 'mag_burn_kmps'].sum())

    final_radper   = float(final.get(f'{sc}.Earth.RadPer', 0))
    final_radapo   = float(final.get(f'{sc}.Earth.RadApo', 0))
    final_inc      = float(final.get(f'{sc}.EarthMJ2000Eq.INC', 0))
    final_ecc      = float(final.get(f'{sc}.Earth.ECC', 0))
    final_sma      = float(final.get(f'{sc}.Earth.SMA', 0))

    rows = [
        ['metric', 'value', 'units'],
        ['initial_altitude_km', f"{LEO_ALT_KM:.1f}", 'km'],
        ['target_altitude_km', f"{GEO_ALT_KM:.1f}", 'km'],
        ['initial_mass_kg', f"{mass_i:.2f}", 'kg'],
        ['final_mass_kg', f"{mass_f:.2f}", 'kg'],
        ['propellant_consumed_kg', f"{prop_consumed:.2f}", 'kg'],
        ['total_delta_v_m_s', f"{total_dv_km_s * 1000:.1f}", 'm/s'],
        ['transfer_time_days', f"{transfer_days:.2f}", 'days'],
        ['final_sma_km', f"{final_sma:.1f}", 'km'],
        ['final_rad_periapsis_km', f"{final_radper:.1f}", 'km'],
        ['final_rad_apoapsis_km', f"{final_radapo:.1f}", 'km'],
        ['final_inclination_deg', f"{final_inc:.4f}", 'deg'],
        ['final_eccentricity', f"{final_ecc:.6f}", ''],
    ]

    csv_path = os.path.join(SIM_DIR, 'results.csv')
    with open(csv_path, 'w') as f:
        for row in rows:
            f.write(','.join(str(x) for x in row) + '\n')

    print(f"[OK] results.csv:")
    for row in rows[1:]:
        print(f"     {row[0]:<30s} {row[1]:>12s}  {row[2]}")


def make_plots():
    """Generate PNG plots using only matplotlib."""
    os.makedirs(PLOTS_DIR, exist_ok=True)

    # ── BurnReportPlotter (matplotlib only) ──────────────────────────────
    if os.path.exists(BURN_CSV):
        try:
            from gmatbard.visualization import BurnReportPlotter
            bp = BurnReportPlotter(BURN_CSV)

            fig = bp.plot_summary_mpl()
            fig.savefig(os.path.join(PLOTS_DIR, 'burn_summary.png'), dpi=150, bbox_inches='tight')
            plt.close(fig)
            print("[OK] burn_summary.png")

            fig = bp.plot_dv_mpl()
            fig.savefig(os.path.join(PLOTS_DIR, 'delta_v.png'), dpi=150, bbox_inches='tight')
            plt.close(fig)
            print("[OK] delta_v.png")

            fig = bp.plot_mass_mpl()
            fig.savefig(os.path.join(PLOTS_DIR, 'mass_history.png'), dpi=150, bbox_inches='tight')
            plt.close(fig)
            print("[OK] mass_history.png")

            fig = bp.plot_orbit_mpl()
            fig.savefig(os.path.join(PLOTS_DIR, 'orbit_elements.png'), dpi=150, bbox_inches='tight')
            plt.close(fig)
            print("[OK] orbit_elements.png")

        except Exception as exc:
            print(f"[WARN] BurnReportPlotter: {exc}")

    # ── EphemerisPlotter (.oem.dat OMERE file) ────────────────────────────
    if os.path.exists(OEM_DAT):
        try:
            from gmatbard.visualization import EphemerisPlotter
            ep_plot = EphemerisPlotter(OEM_DAT)

            fig = ep_plot.plot_summary_mpl()
            fig.savefig(os.path.join(PLOTS_DIR, 'ephemeris_summary.png'), dpi=150, bbox_inches='tight')
            plt.close(fig)
            print("[OK] ephemeris_summary.png")

        except Exception as exc:
            print(f"[WARN] EphemerisPlotter: {exc}")

    # ── TrajectoryPlotter (.oem) ──────────────────────────────────────────
    if os.path.exists(OEM_PATH):
        try:
            from gmatbard.visualization import TrajectoryPlotter
            tp = TrajectoryPlotter(OEM_PATH)

            fig = tp.plot_trajectory_mpl()
            fig.savefig(os.path.join(PLOTS_DIR, 'trajectory_3d.png'), dpi=150, bbox_inches='tight')
            plt.close(fig)
            print("[OK] trajectory_3d.png")

        except Exception as exc:
            print(f"[WARN] TrajectoryPlotter: {exc}")


def main():
    print("=" * 65)
    print("LEO -> GEO Electric Propulsion Spiral Raise")
    print("  Spacecraft: 200 kg (110 dry + 90 EP fuel)")
    print("  Thruster  : 0.2 N / 1800 s Isp")
    print("  LEO: 500 km circular, 28.5 deg inc")
    print("  GEO: 35786 km circular")
    print("=" * 65)

    sim = build_mission()
    if not run_and_parse(sim):
        return

    write_results_csv()
    make_plots()
    print("\nAll done.")


if __name__ == "__main__":
    main()
