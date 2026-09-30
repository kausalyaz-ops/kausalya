"""Five publication-ready visualizations of the observed extract."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


class VisualizationManager:
    """Render the required chart suite to a stable output directory."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        plt.style.use("seaborn-v0_8-whitegrid")

    def render_all(self, frame: pd.DataFrame, departments: pd.DataFrame, annual: pd.DataFrame) -> list[str]:
        self._bar_chart(departments)
        self._annual_records(annual)
        self._salary_histogram(frame)
        self._hours_salary_scatter(frame)
        self._department_share(departments)
        return [
            "average_salary_by_department.png",
            "annual_compensation_records.png",
            "salary_distribution.png",
            "hours_vs_salary.png",
            "department_record_share.png",
        ]

    def _bar_chart(self, departments: pd.DataFrame) -> None:
        data = departments.nlargest(12, "avg_salary").sort_values("avg_salary")
        fig, ax = plt.subplots(figsize=(11, 6))
        ax.barh(data["department"], data["avg_salary"], color="#087E8B", label="Mean record salary")
        ax.set(title="Average Record Salary by Department (Top 12)", xlabel="Mean salary (USD)", ylabel="Department")
        ax.grid(axis="x", alpha=0.25)
        ax.legend(frameon=False)
        self._save(fig, "average_salary_by_department.png")

    def _annual_records(self, annual: pd.DataFrame) -> None:
        fig, ax = plt.subplots(figsize=(10, 5.5))
        ax.plot(annual["year"], annual["compensation_records"], marker="o", color="#D1495B", label="Compensation records")
        ax.set(title="Annual Compensation Record Volume", xlabel="Fiscal year", ylabel="Records in extract")
        ax.set_xticks(annual["year"].astype(int))
        ax.grid(alpha=0.3)
        ax.legend(frameon=False)
        self._save(fig, "annual_compensation_records.png")

    def _salary_histogram(self, frame: pd.DataFrame) -> None:
        fig, ax = plt.subplots(figsize=(10, 5.5))
        ax.hist(frame["salary"], bins=35, color="#F4A259", edgecolor="white", label="Compensation records")
        ax.set(title="Distribution of Record Salaries", xlabel="Salary (USD)", ylabel="Frequency")
        ax.grid(axis="y", alpha=0.3)
        ax.legend(frameon=False)
        self._save(fig, "salary_distribution.png")

    def _hours_salary_scatter(self, frame: pd.DataFrame) -> None:
        fig, ax = plt.subplots(figsize=(10, 5.5))
        points = ax.scatter(frame["hours"], frame["salary"], c=frame["year"], cmap="viridis", alpha=0.45, s=18, label="Compensation record")
        ax.set(title="Hours Worked vs. Record Salary", xlabel="Reported hours", ylabel="Salary (USD)")
        ax.grid(alpha=0.25)
        fig.colorbar(points, ax=ax, label="Fiscal year")
        ax.legend(frameon=False)
        self._save(fig, "hours_vs_salary.png")

    def _department_share(self, departments: pd.DataFrame) -> None:
        data = departments.nlargest(7, "record_count").copy()
        other_count = int(departments["record_count"].sum() - data["record_count"].sum())
        if other_count > 0:
            data.loc[len(data)] = {"department": "Other departments", "record_count": other_count}
        fig, ax = plt.subplots(figsize=(8, 7))
        ax.pie(
            data["record_count"],
            labels=data["department"],
            autopct="%1.1f%%",
            startangle=90,
            wedgeprops={"width": 0.42, "edgecolor": "white"},
            colors=plt.get_cmap("Set2").colors[: len(data)],
        )
        ax.set_title("Share of Compensation Records by Department")
        ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), frameon=False, title="Department")
        self._save(fig, "department_record_share.png")

    def _save(self, figure: plt.Figure, filename: str) -> None:
        figure.tight_layout()
        figure.savefig(self.output_dir / filename, dpi=160, bbox_inches="tight")
        plt.close(figure)