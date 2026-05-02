"""core.statistics

Statistics and plotting helpers for simulation outputs.

This module provides:
- Per-room summary statistics (mean/std/min/max/median/range).
- Aggregate statistics over a time series of State snapshots.
- Matplotlib visualizations (heatmap, time-series dashboards, comparisons).
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from .state.state import State

class Statistics:
    """Compute and visualize temperature and energy statistics."""

    def compute_room_statistics(self, state: State) -> dict[str, dict[str, float]]:
        """
        Provided function.

        Compute descriptive temperature statistics for each room type present
        in the current state.  Room type 'x' (walls, doors, unlabelled cells)
        is excluded from all calculations.

        Args:
            state: State instance whose `floor_map.room_types` and
                   `temperature_field` are read.

        Returns:
            A dict mapping each room type character (e.g. 'A', 'B') to a
            nested dict of statistics over all cells of that room type:
                'mean'   (float): mean temperature across cells of this room type.
                'std'    (float): standard deviation of temperatures.
                'min'    (float): minimum cell temperature.
                'max'    (float): maximum cell temperature.
                'count'  (int):   number of cells belonging to this room type.
                'median' (float): median temperature.
                'range'  (float): max - min temperature (spread).
            Room types with no cells on this map are omitted from the dict.
        """
        result = {}
        for room_type in np.unique(state.floor_map.room_types):
            # Skip non-room cells (walls, doors, unlabelled corridors)
            if room_type == 'x':
                continue

            # Boolean mask selecting all cells belonging to this room type
            room_mask = (state.floor_map.room_types == room_type)
            room_temps = state.temperature_field[room_mask]

            if len(room_temps) > 0:
                result[room_type] = {
                    'mean':   float(np.mean(room_temps)),
                    'std':    float(np.std(room_temps)),
                    'min':    float(np.min(room_temps)),
                    'max':    float(np.max(room_temps)),
                    'count':  int(len(room_temps)),
                    'median': float(np.median(room_temps)),
                    'range':  float(np.max(room_temps) - np.min(room_temps)),
                }

        return result
    
    def compute_time_series_statistics(self, state_history: list[State]) -> dict[str, dict[str, float]]:
        """
        Provided function.

        Aggregate temperature, energy, and score statistics over a sequence of
        simulation snapshots.  Room type 'x' is excluded from all temperature
        calculations.

        Per-room temperature statistics are derived by calling
        `compute_room_statistics` on each snapshot, then summarising the
        resulting per-step mean temperatures across time.

        Per-AC energy statistics are accumulated directly from
        `state.energy_dict` at each snapshot.

        Score statistics are derived from `state.score` at each snapshot,
        where `state.score = (total, comfort, uniformity, energy)`.

        Args:
            state_history: Ordered list of State snapshots, one per simulated
                           minute.  Returns an empty dict if the list is empty.

        Returns:
            A flat dict with the following keys:

            Temperature (per room type, keyed by room type character):
                'mean_temp_mean' (dict[str, float]):
                    For each room type, the mean of its per-step mean temperatures
                    across all snapshots — i.e. the time-averaged mean temperature.
                'mean_temp_std'  (dict[str, float]):
                    For each room type, the standard deviation of its per-step mean
                    temperatures across all snapshots — i.e. how much the room's
                    average temperature fluctuates over time.

            Energy (per AC unit, keyed by AC name):
                'energy_total' (dict[str, float]):
                    Total energy consumed by each AC over all snapshots.
                'energy_mean'  (dict[str, float]):
                    Mean energy consumed by each AC per snapshot (step).
                'energy_std'   (dict[str, float]):
                    Standard deviation of per-step energy for each AC.

            Scores (scalar floats, averaged over all snapshots):
                'total_score_mean', 'total_score_std':
                    Mean and std of the composite total score.
                'comfort_score_mean', 'comfort_score_std':
                    Mean and std of the comfort score component.
                'uniformity_score_mean', 'uniformity_score_std':
                    Mean and std of the uniformity score component.
                'energy_score_mean', 'energy_score_std':
                    Mean and std of the energy score component.
        """
        
        n_steps = len(state_history)
        if n_steps == 0:
            return {}

        # --- Temperature statistics ---
        # Compute per-room statistics at each step, then summarize the mean-temperature series
        per_step_room_stats = [self.compute_room_statistics(state) for state in state_history]
        room_mean_history: dict[str, list[float]] = {}  # room_type -> [mean_at_step_0, mean_at_step_1, ...]

        for step_stats in per_step_room_stats:
            for room_type, room_stat in step_stats.items():
                if room_type not in room_mean_history:
                    room_mean_history[room_type] = []
                room_mean_history[room_type].append(room_stat['mean'])

        mean_temp_by_room = {rt: np.mean(means) for rt, means in room_mean_history.items()}
        std_temp_by_room  = {rt: np.std(means)  for rt, means in room_mean_history.items()}

        # --- Energy statistics ---
        # Accumulate sum and sum-of-squares for each AC to compute mean and std in one pass
        energy_totals: dict[str, float] = {}
        energy_sum_sq: dict[str, float] = {}  # sum of energy^2 per AC, used for std via E[X^2]-(E[X])^2

        for state in state_history:
            for ac_name, energy in state.energy_dict.items():
                if ac_name not in energy_totals:
                    energy_totals[ac_name] = 0.0
                    energy_sum_sq[ac_name] = 0.0
                energy_totals[ac_name] += energy
                energy_sum_sq[ac_name] += energy ** 2

        mean_energy_by_ac = {ac: total / n_steps for ac, total in energy_totals.items()}
        # Single-pass std formula: std = sqrt(E[X^2] - (E[X])^2)
        std_energy_by_ac = {
            ac: np.sqrt((sq / n_steps) - (mean_energy_by_ac[ac] ** 2))
            for ac, sq in energy_sum_sq.items()
        }

        # --- Score statistics ---
        # state.score = (total, comfort, uniformity, energy)
        total_scores      = [state.score[0] for state in state_history]
        comfort_scores    = [state.score[1] for state in state_history]
        uniformity_scores = [state.score[2] for state in state_history]
        energy_scores     = [state.score[3] for state in state_history]

        return {
            'mean_temp_mean':        mean_temp_by_room,
            'mean_temp_std':         std_temp_by_room,
            'energy_total':          energy_totals,
            'energy_mean':           mean_energy_by_ac,
            'energy_std':            std_energy_by_ac,
            'total_score_mean':      float(np.mean(total_scores)),
            'total_score_std':       float(np.std(total_scores)),
            'comfort_score_mean':    float(np.mean(comfort_scores)),
            'comfort_score_std':     float(np.std(comfort_scores)),
            'uniformity_score_mean': float(np.mean(uniformity_scores)),
            'uniformity_score_std':  float(np.std(uniformity_scores)),
            'energy_score_mean':     float(np.mean(energy_scores)),
            'energy_score_std':      float(np.std(energy_scores)),
        }
    
    def plot_temperature_heatmap(self, state: State) -> Figure:
        """
        Provided function.

        Plot temperature heatmap using matplotlib.
        
        Args:
            state: State instance.

        Returns:
            matplotlib Figure.

        Usage:
            fig = stats.plot_temperature_heatmap(state)
            fig.savefig('heatmap.png')   # save to file
            fig.show()                   # display interactively
            plt.show()                   # alternative: display via pyplot
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        im = ax.imshow(state.temperature_field, cmap='coolwarm', interpolation='nearest')
        ax.set_title('Temperature Heatmap')
        ax.set_xlabel('Column')
        ax.set_ylabel('Row')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Temperature (°C)')
        
        # Add grid
        ax.set_xticks(np.arange(-0.5, state.floor_map.width, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, state.floor_map.height, 1), minor=True)
        ax.grid(which='minor', color='gray', linestyle='-', linewidth=0.5)
        
        plt.tight_layout()
        return fig
    
    def plot_time_series(self, state_history: list[State]) -> Figure | None:
        """
        Provided function.

        Plot time series trends aligned with `compute_time_series_statistics`.
        Depend on correctness of `compute_time_series_statistics` function.

        This visualizes:
          - Mean temperature per room type over time (vs Target/Outdoor)
          - Energy usage per AC over time (step energy + cumulative)
          - Score components over time (total/comfort/uniformity/energy)

        Returns:
            matplotlib Figure, or None if the series is empty.

        Usage:
            fig = stats.plot_time_series(state_history)
            if fig is not None:
                fig.savefig('time_series.png')    # save to file
                fig.show()                        # display interactively
                plt.show()                        # alternative: display via pyplot
        """
        n_steps = len(state_history)

        if n_steps == 0:
            return None

        timesteps = np.arange(n_steps)

        # Collect basic series
        room_types = sorted([rt for rt in np.unique(state_history[0].floor_map.room_types) if rt != 'x'])
        room_mean_series = {rt: [] for rt in room_types}
        room_stddev_series = {rt: [] for rt in room_types}
        
        # Also collect environment history
        outdoor_temps = []
        setpoint_temps = []

        for state in state_history:
            step_stats = self.compute_room_statistics(state)
            outdoor_temps.append(state.outdoor_temp)
            setpoint_temps.append(state.setpoint_temp)
            
            for rt in room_types:
                # If a room type does not appear at some step, mark as NaN
                room_mean_series[rt].append(step_stats.get(rt, {}).get('mean', np.nan))
                room_stddev_series[rt].append(step_stats.get(rt, {}).get('std', np.nan))

        # Energy processing
        energy_dicts = []
        for state in state_history:
            e = state.energy_dict
            if isinstance(e, dict):
                energy_dicts.append(e)
            else:
                # Fallback if energy was stored as single float (old format)
                energy_dicts.append({"total": float(e)})

        ac_names = sorted({ac for d in energy_dicts for ac in d.keys()})
        step_energy = {ac: np.zeros(n_steps, dtype=float) for ac in ac_names}

        for i, d in enumerate(energy_dicts):
            for ac in ac_names:
                step_energy[ac][i] = float(d.get(ac, 0.0))

        cumulative_energy = {ac: np.cumsum(vals) for ac, vals in step_energy.items()}

        # Scores
        total_scores = [state.score[0] for state in state_history]
        comfort_scores = [state.score[1] for state in state_history]
        uniformity_scores = [state.score[2] for state in state_history]
        energy_scores = [state.score[3] for state in state_history]

        fig, axes = plt.subplots(2, 2, figsize=(16, 10))

        # -------------------------------------------------------------------------
        # 1. Mean Temperature vs Target/Outdoor
        # -------------------------------------------------------------------------
        ax = axes[0, 0]
        # Draw dynamic reference lines first (so they are behind)
        ax.plot(timesteps, setpoint_temps, color='red', linestyle='--', label='Target Temp')
        ax.plot(timesteps, outdoor_temps, color='purple', linestyle='--', label='Outdoor Temp')
        
        for rt in room_types:
            ax.plot(timesteps, room_mean_series[rt], linewidth=2, label=f"Room {rt}")
            
        ax.set_xlabel('Time (minutes)')
        ax.set_ylabel('Mean Temperature (°C)')
        ax.set_title('Mean Temperature by Room Type Over Time')
        ax.grid(True)
        ax.legend(ncol=2)

        # -------------------------------------------------------------------------
        # 2. Temperature Std Dev (Uniformity)
        # -------------------------------------------------------------------------
        ax = axes[0, 1]
        for rt in room_types:
            ax.plot(timesteps, room_stddev_series[rt], linewidth=2, label=f"Room {rt}")
        ax.set_xlabel('Time (minutes)')
        ax.set_ylabel('Temperature Std Dev (°C)')
        ax.set_title('Temperature Uniformity by Room Type Over Time')
        ax.grid(True)
        ax.legend(ncol=2)

        # -------------------------------------------------------------------------
        # 3. Cumulative Energy
        # -------------------------------------------------------------------------
        ax = axes[1, 0]
        for ac in ac_names:
            ax.plot(timesteps, cumulative_energy[ac], linewidth=2, label=str(ac))
        ax.set_xlabel('Time (minutes)')
        ax.set_ylabel('Cumulative Energy')
        ax.set_title('Cumulative Energy Consumption (by AC)')
        ax.grid(True)
        ax.legend()

        # -------------------------------------------------------------------------
        # 4. Scores
        # -------------------------------------------------------------------------
        ax = axes[1, 1]
        ax.plot(timesteps, total_scores, 'purple', linewidth=2, label='Total')
        ax.plot(timesteps, comfort_scores, 'r-', linewidth=2, label='Comfort')
        ax.plot(timesteps, uniformity_scores, color='orange', linewidth=2, label='Uniformity')
        ax.plot(timesteps, energy_scores, 'g-', linewidth=2, label='Energy')
        ax.set_xlabel('Time (minutes)')
        ax.set_ylabel('Score')
        ax.set_title('Score Components Over Time')
        ax.grid(True)
        ax.legend()

        plt.tight_layout()
        return fig
    
    def plot_room_comparison(self, state: State) -> Figure | None:
        """
        Provided function

        Plot bar chart comparing statistics across rooms.
        Depend on correctness of `compute_room_statistics` function.
        
        Args:
            state: State instance.

        Returns:
            matplotlib Figure, or None if no rooms are present.

        Usage:
            fig = stats.plot_room_comparison(state)
            if fig is not None:
                fig.savefig('room_comparison.png')   # save to file
                fig.show()                            # display interactively
                plt.show()                            # alternative: display via pyplot
        """

        room_stats = self.compute_room_statistics(state)

        room_types = sorted(room_stats.keys())
        room_means = [room_stats[rt]['mean'] for rt in room_types]  # mean temperature per room
        room_stds  = [room_stats[rt]['std']  for rt in room_types]  # std dev per room

        # Reference temperature lines for visual context
        target  = state.setpoint_temp
        outdoor = state.outdoor_temp

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Left panel: mean temperature per room vs reference lines
        ax = axes[0]
        ax.bar(room_types, room_means, color='skyblue', label='Room Mean')
        # Horizontal reference lines for target and outdoor temperatures
        ax.axhline(y=target,  color='red',    linestyle='--', label=f'Target ({target:.1f})')
        ax.axhline(y=outdoor, color='purple', linestyle='--', label=f'Outdoor ({outdoor:.1f})')

        ax.set_xlabel('Room Type')
        ax.set_ylabel('Mean Temperature (°C)')
        ax.set_title('Mean Temperature by Room')
        ax.grid(axis='y')
        ax.legend()

        # Right panel: temperature std dev per room (lower = more uniform)
        axes[1].bar(room_types, room_stds, color='coral', label='Room Std Dev')
        axes[1].set_xlabel('Room Type')
        axes[1].set_ylabel('Temperature Std Dev (°C)')
        axes[1].set_title('Temperature Uniformity by Room')
        axes[1].grid(axis='y')

        plt.tight_layout()
        return fig

    def __repr__(self) -> str:
        """
        Provided function.
        Short debug representation.

        e.g.: print(stats)
        """
        return f"Statistics()"