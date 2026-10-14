import argparse
import csv
import math
from pathlib import Path

import matplotlib

# 창을 띄우지 않고 그래프를 이미지로 저장합니다.
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# 단면적 단위: mm². N/mm²는 MPa와 같습니다.
area_mm2 = 100
stress_threshold_mpa = 6


def analyze_load(file_path, result_path=None, plot_path=None):
    if not math.isfinite(area_mm2) or area_mm2 <= 0:
        raise ValueError("단면적은 0보다 큰 유한한 숫자여야 합니다.")

    result_rows = []
    count = 0
    excluded_count = 0
    max_force = None
    max_time = None

    with file_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not {"time_s", "force_N"}.issubset(reader.fieldnames or []):
            raise ValueError("CSV에 time_s와 force_N 열이 필요합니다.")

        for row in reader:
            values = {}
            problems = []
            for column in ("time_s", "force_N"):
                raw_value = row.get(column)
                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    problems.append(
                        f"{column}={raw_value!r} (빈칸 또는 숫자가 아님)"
                    )
                    continue
                if not math.isfinite(value):
                    problems.append(
                        f"{column}={raw_value!r} (유한한 숫자가 아님)"
                    )
                    continue
                values[column] = value

            if problems:
                excluded_count += 1
                print(f"CSV {reader.line_num}행 제외: {', '.join(problems)}")
                continue

            time = values["time_s"]
            force = values["force_N"]

            stress = force / area_mm2
            result_rows.append({
                "time_s": time,
                "force_N": force,
                "stress_MPa": stress,
            })
            count += 1
            # 최대 하중이 같으면 처음 나온 시간을 유지합니다.
            if max_force is None or force > max_force:
                max_force = force
                max_time = time

    print(f"제외한 행 수: {excluded_count}")
    print(f"유효한 데이터 수: {count}")
    if count == 0:
        raise ValueError("유효한 데이터가 없습니다. 계산을 중단합니다.")

    # 기준값과 같은 응력은 제외하고, 초과한 데이터만 셉니다.
    exceed_count = sum(
        row["stress_MPa"] > stress_threshold_mpa for row in result_rows
    )
    print(
        f"기준 응력 {stress_threshold_mpa:g} MPa 초과 데이터 개수: {exceed_count}"
    )
    if result_path is not None:
        if file_path.resolve() == result_path.resolve():
            raise ValueError("결과 파일은 원본 파일과 달라야 합니다.")
        with result_path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(
                file, fieldnames=["time_s", "force_N", "stress_MPa"]
            )
            writer.writeheader()
            writer.writerows(result_rows)

    if plot_path is not None:
        save_stress_plot(result_rows, plot_path, file_path.name)

    return count, max_force, max_time


def save_stress_plot(data, plot_path, source_name="load_data.csv"):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    try:
        ax.plot(
            [row["time_s"] for row in data],
            [row["stress_MPa"] for row in data],
            marker="o",
        )
        max_point = max(data, key=lambda row: row["stress_MPa"])
        max_time = max_point["time_s"]
        max_stress = max_point["stress_MPa"]
        ax.scatter(max_time, max_stress, color="red", s=70, zorder=3)
        ax.annotate(
            f"Max: {max_time:g} s, {max_stress:g} MPa",
            xy=(max_time, max_stress),
            xytext=(20, -25),
            textcoords="offset points",
            color="red",
            fontsize=10,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.85),
            arrowprops=dict(arrowstyle="->", color="red", linewidth=0.8),
        )
        ax.set_title(
            f"Stress vs. Time\n{source_name}, Area = {area_mm2:g} mm²"
        )
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Stress (MPa)")
        ax.set_xticks([row["time_s"] for row in data])
        ax.set_axisbelow(True)
        ax.grid(True, color="lightgray", linewidth=0.6, alpha=0.6)
        fig.tight_layout()
        fig.savefig(plot_path, dpi=150)
    finally:
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="CSV 하중 및 응력 분석")
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent / "load_data.csv",
        help="입력 CSV 파일 (기본값: load_data.csv)",
    )
    file_path = parser.parse_args().csv_path
    result_path = file_path.parent / "load_result.csv"
    plot_path = file_path.parent / "stress_plot.png"
    try:
        count, max_force, max_time = analyze_load(file_path, result_path, plot_path)
    except (OSError, ValueError, csv.Error) as error:
        print(f"오류: {error}")
        return 1

    print(f"데이터 개수: {count}")
    print(f"최대 하중: {max_force:g} N")
    print(f"최대 하중 발생 시간: {max_time:g} s")
    print(f"최대 응력: {max_force / area_mm2:g} MPa")
    print(f"최대 응력 발생 시간: {max_time:g} s")
    print(f"결과 저장: {result_path.name}")
    print(f"그래프 저장: {plot_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
