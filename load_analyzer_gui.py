import csv
import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


REQUIRED_COLUMNS = ("time_s", "force_N")

# 단면 종류별 치수 입력칸(이름, 화면 표시), 단면적 계산식, 치수 조건입니다.
# 치수는 mm, 단면적은 mm²입니다. 단면을 추가할 때 이 표에 항목을 더합니다.
# "check"는 모든 치수가 0보다 크다는 검사를 통과한 뒤 실행하며,
# 불가능한 치수이면 안내 문구를, 괜찮으면 None을 돌려줍니다.
SECTIONS = {
    "사각형": {
        "fields": [("b", "폭 b (mm)"), ("h", "높이 h (mm)")],
        "area": lambda d: d["b"] * d["h"],
        "check": lambda d: None,
    },
    "원형봉": {
        "fields": [("d", "지름 d (mm)")],
        "area": lambda d: math.pi * d["d"] ** 2 / 4,
        "check": lambda d: None,
    },
    "원형관": {
        "fields": [("D", "외경 D (mm)"), ("t", "두께 t (mm)")],
        "area": lambda d: math.pi * (d["D"] ** 2 - (d["D"] - 2 * d["t"]) ** 2) / 4,
        "check": lambda d: (
            None
            if 2 * d["t"] < d["D"]
            else "두께 t의 2배가 외경 D보다 작아야 합니다. (내부 공간이 없습니다)"
        ),
    },
    "사각형관": {
        "fields": [
            ("B", "외측 폭 B (mm)"),
            ("H", "외측 높이 H (mm)"),
            ("t", "두께 t (mm)"),
        ],
        "area": lambda d: d["B"] * d["H"] - (d["B"] - 2 * d["t"]) * (d["H"] - 2 * d["t"]),
        "check": lambda d: (
            None
            if 2 * d["t"] < d["B"] and 2 * d["t"] < d["H"]
            else "두께 t의 2배가 외측 폭 B와 외측 높이 H보다 모두 작아야 합니다. (내부 공간이 없습니다)"
        ),
    },
    "H형강": {
        "fields": [
            ("H", "전체 높이 H (mm)"),
            ("B", "플랜지 폭 B (mm)"),
            ("tw", "웨브 두께 tw (mm)"),
            ("tf", "플랜지 두께 tf (mm)"),
        ],
        "area": lambda d: 2 * d["B"] * d["tf"] + (d["H"] - 2 * d["tf"]) * d["tw"],
        "check": lambda d: (
            "플랜지 두께 tf의 2배가 전체 높이 H보다 작아야 합니다."
            if not 2 * d["tf"] < d["H"]
            else "웨브 두께 tw가 플랜지 폭 B보다 작아야 합니다."
            if not d["tw"] < d["B"]
            else None
        ),
    },
}


def read_load_csv(file_path):
    """CSV에서 유효한 (time_s, force_N) 행을 읽습니다.

    load_analyzer.py와 같은 규칙을 사용합니다. 빈칸, 숫자가 아닌 값,
    NaN·무한대가 있는 행은 제외하고, 시간순으로 정렬해 돌려줍니다.
    반환값: (유효 행 목록, 제외한 행 수)
    """
    rows = []
    excluded_count = 0

    with Path(file_path).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not set(REQUIRED_COLUMNS).issubset(reader.fieldnames or []):
            raise ValueError("CSV에 time_s와 force_N 열이 필요합니다.")

        for row in reader:
            values = {}
            for column in REQUIRED_COLUMNS:
                try:
                    value = float(row.get(column))
                except (TypeError, ValueError):
                    break
                if not math.isfinite(value):
                    break
                values[column] = value
            else:
                rows.append(values)
                continue
            excluded_count += 1

    rows.sort(key=lambda row: row["time_s"])
    return rows, excluded_count


def parse_dimensions(section_name, raw_values):
    """입력 문자열을 검사해 {이름: 값(mm)} 으로 바꿉니다. 잘못되면 ValueError."""
    dimensions = {}
    for name, field_label in SECTIONS[section_name]["fields"]:
        label = field_label.split(" (")[0]  # 안내 문구에는 단위를 뺍니다.
        text = raw_values[name].strip()
        if not text:
            raise ValueError(f"{label}을(를) 입력하세요.")
        try:
            value = float(text)
        except ValueError:
            raise ValueError(f"{label}은(는) 숫자로 입력하세요. (입력값: {text})")
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{label}은(는) 0보다 큰 유한한 숫자여야 합니다.")
        dimensions[name] = value
    return dimensions


def compute_section_area(section_name, raw_values):
    """단면적(mm²)을 계산합니다. 치수가 잘못되면 ValueError."""
    dimensions = parse_dimensions(section_name, raw_values)
    problem = SECTIONS[section_name]["check"](dimensions)
    if problem:
        raise ValueError(problem)
    try:
        area = SECTIONS[section_name]["area"](dimensions)
    except OverflowError:  # float ** 2 가 너무 커지는 경우
        area = math.inf
    if not math.isfinite(area) or area <= 0:
        raise ValueError("치수가 너무 커서 단면적을 계산할 수 없습니다.")
    return area


def analyze_stress(rows, area_mm2):
    """응력(MPa) = 하중(N) / 단면적(mm²). 최대 하중이 같으면 먼저 나온 시간을 씁니다."""
    stresses = [
        {
            "time_s": row["time_s"],
            "force_N": row["force_N"],
            "stress_MPa": row["force_N"] / area_mm2,
        }
        for row in rows
    ]
    peak = max(stresses, key=lambda row: row["stress_MPa"])
    return {
        "area_mm2": area_mm2,
        "rows": stresses,
        "max_force_N": peak["force_N"],
        "max_stress_MPa": peak["stress_MPa"],
        "max_time_s": peak["time_s"],
    }


def format_number(value):
    """1,234.5 처럼 천 단위 구분을 쓰고, 불필요한 소수 0은 뺍니다."""
    return f"{value:,.2f}".rstrip("0").rstrip(".")


NO_RESULT = "—"


class LoadAnalyzerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("하중 데이터 분석기")
        self.geometry("900x820")
        self.minsize(680, 640)

        self.rows = []          # 현재 CSV의 유효 데이터
        self.csv_problem = None  # CSV를 쓸 수 없는 이유(정상이면 None)
        self.analysis = None    # 현재 조건에 대한 분석 결과(없으면 None)
        self.dimension_vars = {}
        self.dimension_error = False  # 화면의 오류 안내가 치수 입력 때문인지

        self.path_var = tk.StringVar()
        self.count_var = tk.StringVar()
        self.detail_var = tk.StringVar()
        self.message_var = tk.StringVar()
        self.section_var = tk.StringVar(value=next(iter(SECTIONS)))
        self.area_var = tk.StringVar(value=NO_RESULT)
        self.result_vars = {
            key: tk.StringVar(value=NO_RESULT)
            for key in ("area", "max_force", "max_stress", "max_time")
        }

        self._build_widgets()
        self._build_dimension_fields()
        self._show_count(0, None)
        self._set_message("CSV 파일을 선택하세요.")
        self._draw_plot()

    # ---------- 화면 구성 ----------
    def _build_widgets(self):
        top = ttk.Frame(self, padding=(10, 10, 10, 0))
        top.pack(fill="x")
        ttk.Button(top, text="CSV 찾아보기", command=self.browse_csv).pack(
            side="left"
        )
        ttk.Entry(top, textvariable=self.path_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=(8, 0)
        )

        info = ttk.Frame(self, padding=(10, 10, 10, 0))
        info.pack(fill="x")
        count_row = ttk.Frame(info)
        count_row.pack(fill="x")
        ttk.Label(
            count_row, textvariable=self.count_var, font=("", 11, "bold")
        ).pack(side="left")
        ttk.Label(count_row, textvariable=self.detail_var).pack(
            side="left", padx=(12, 0)
        )
        ttk.Label(
            info,
            text="필수 열: time_s, force_N · 빈칸, 문자, 무한대가 있는 행은 제외합니다.",
        ).pack(anchor="w", pady=(6, 0))
        self.message_label = ttk.Label(info, textvariable=self.message_var)
        self.message_label.pack(anchor="w", pady=(6, 0))

        section_frame = ttk.LabelFrame(self, text="단면", padding=8)
        section_frame.pack(fill="x", padx=10, pady=(10, 0))

        type_row = ttk.Frame(section_frame)
        type_row.pack(fill="x")
        ttk.Label(type_row, text="단면 종류").pack(side="left")
        combo = ttk.Combobox(
            type_row,
            textvariable=self.section_var,
            values=list(SECTIONS),
            state="readonly",
            width=12,
        )
        combo.pack(side="left", padx=(8, 16))
        combo.bind("<<ComboboxSelected>>", self._on_section_selected)
        ttk.Button(type_row, text="분석", command=self.run_analysis).pack(
            side="left"
        )

        self.dimension_frame = ttk.Frame(section_frame)
        self.dimension_frame.pack(fill="x", pady=(8, 0))

        area_row = ttk.Frame(section_frame)
        area_row.pack(fill="x", pady=(8, 0))
        ttk.Label(area_row, text="단면적 A").pack(side="left")
        ttk.Label(area_row, textvariable=self.area_var, font=("", 10, "bold")).pack(
            side="left", padx=(8, 0)
        )

        result_frame = ttk.LabelFrame(self, text="분석 결과", padding=8)
        result_frame.pack(fill="x", padx=10, pady=(10, 0))
        for column, (label, key) in enumerate(
            [
                ("단면적", "area"),
                ("최대 하중", "max_force"),
                ("최대 응력", "max_stress"),
                ("발생 시간", "max_time"),
            ]
        ):
            cell = ttk.Frame(result_frame)
            cell.grid(row=0, column=column, sticky="w", padx=(0, 28))
            ttk.Label(cell, text=label).pack(anchor="w")
            ttk.Label(
                cell, textvariable=self.result_vars[key], font=("", 12, "bold")
            ).pack(anchor="w")

        self.plot_frame = ttk.LabelFrame(self, text="", padding=6)
        self.plot_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.figure = Figure(figsize=(8, 4.5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _build_dimension_fields(self):
        """선택한 단면에 필요한 치수 입력칸만 보여줍니다."""
        for child in self.dimension_frame.winfo_children():
            child.destroy()
        self.dimension_vars = {}
        for name, label in SECTIONS[self.section_var.get()]["fields"]:
            var = tk.StringVar()
            var.trace_add("write", self._on_condition_changed)
            self.dimension_vars[name] = var
            ttk.Label(self.dimension_frame, text=label).pack(side="left")
            entry = ttk.Entry(self.dimension_frame, textvariable=var, width=10)
            entry.pack(side="left", padx=(6, 16))
            entry.bind("<Return>", lambda _event: self.run_analysis())

    def _on_section_selected(self, _event=None):
        # 이전 단면 기준의 치수 오류 안내는 새 단면에 맞지 않으므로 지웁니다.
        if self.dimension_error:
            self._set_message("")
        self._build_dimension_fields()
        self._on_condition_changed()

    # ---------- 동작 ----------
    def browse_csv(self):
        file_path = filedialog.askopenfilename(
            title="CSV 파일 선택",
            filetypes=[("CSV 파일", "*.csv"), ("모든 파일", "*.*")],
        )
        # 취소하면 빈 문자열이 오므로 현재 화면을 그대로 유지합니다.
        if file_path:
            self.load_csv(file_path)

    def load_csv(self, file_path):
        self.path_var.set(str(file_path))
        # 새 파일을 고르면 이전 응력 결과는 지웁니다.
        self._clear_analysis()
        try:
            rows, excluded_count = read_load_csv(file_path)
        except (OSError, ValueError, csv.Error, UnicodeDecodeError) as error:
            # 실패하면 이전 파일의 데이터를 남기지 않습니다.
            self.rows = []
            self.csv_problem = f"오류: {error}"
            self._show_count(0, None)
            self._set_message(self.csv_problem, error=True)
            self._draw_plot()
            return

        self.rows = rows
        self.csv_problem = None
        total = len(rows) + excluded_count
        self._show_count(len(rows), (total, excluded_count))
        if rows:
            self._set_message(
                "유효한 데이터를 시간순으로 표시했습니다.", ok=True
            )
        else:
            self.csv_problem = "유효한 데이터가 없습니다. 분석을 멈춥니다."
            self._set_message(self.csv_problem, error=True)
        self._draw_plot()

    def run_analysis(self):
        """분석 버튼: 단면적 계산 → 응력 계산 → 결과 표시 → 그래프 갱신."""
        # 실패해도 이전 결과가 현재 결과처럼 남지 않도록 먼저 지웁니다.
        self._clear_analysis()
        if not self.rows:
            self._set_message(
                self.csv_problem or "CSV 파일을 먼저 선택하세요.", error=True
            )
            self._draw_plot()
            return

        raw_values = {name: var.get() for name, var in self.dimension_vars.items()}
        try:
            area = compute_section_area(self.section_var.get(), raw_values)
        except ValueError as error:
            self._set_message(f"오류: {error}", error=True)
            self.dimension_error = True
            self._draw_plot()
            return

        self.analysis = analyze_stress(self.rows, area)
        self._show_results()
        self._set_message("분석을 완료했습니다. 시간–응력 그래프로 갱신했습니다.", ok=True)
        self._draw_plot()

    def _on_condition_changed(self, *_args):
        """치수나 단면 종류가 바뀌면 단면적 미리보기를 갱신하고 이전 결과를 무효로 합니다."""
        try:
            area = compute_section_area(
                self.section_var.get(),
                {name: var.get() for name, var in self.dimension_vars.items()},
            )
            self.area_var.set(f"{format_number(area)} mm²")
            if self.dimension_error:
                self._set_message("입력을 고쳤습니다. 분석 버튼을 눌러 주세요.", ok=True)
        except ValueError:
            self.area_var.set(NO_RESULT)

        if self.analysis is not None:
            self._clear_analysis()
            self._set_message("조건 변경됨: 다시 분석 필요", error=True)
            self._draw_plot()

    def _clear_analysis(self):
        self.analysis = None
        for var in self.result_vars.values():
            var.set(NO_RESULT)

    # ---------- 표시 ----------
    def _show_count(self, valid_count, totals):
        self.count_var.set(f"유효 데이터 수: {valid_count}개")
        if totals is None:
            self.detail_var.set("")
        else:
            total, excluded = totals
            self.detail_var.set(f"전체 {total}개 / 제외 {excluded}개")

    def _set_message(self, text, error=False, ok=False):
        self.dimension_error = False
        self.message_var.set(text)
        color = "#b00020" if error else "#1b5e20" if ok else ""
        self.message_label.configure(foreground=color)

    def _show_results(self):
        result = self.analysis
        self.result_vars["area"].set(f"{format_number(result['area_mm2'])} mm²")
        self.result_vars["max_force"].set(f"{format_number(result['max_force_N'])} N")
        self.result_vars["max_stress"].set(
            f"{format_number(result['max_stress_MPa'])} MPa"
        )
        self.result_vars["max_time"].set(f"{format_number(result['max_time_s'])} s")

    def _draw_plot(self):
        """분석 결과가 있으면 시간–응력, 없으면 시간–하중 그래프를 그립니다."""
        ax = self.ax
        ax.clear()
        if self.analysis is not None:
            data = self.analysis["rows"]
            key, ylabel, title = "stress_MPa", "Stress (MPa)", "시간–응력 그래프"
        else:
            data = self.rows
            key, ylabel, title = "force_N", "Force (N)", "시간–하중 그래프"
        self.plot_frame.configure(text=title)

        if data:
            times = [row["time_s"] for row in data]
            values = [row[key] for row in data]
            ax.plot(times, values, marker="o", color="#3b78d8", linewidth=2)
            if self.analysis is not None:
                peak_time = self.analysis["max_time_s"]
                peak_value = self.analysis["max_stress_MPa"]
                ax.scatter(peak_time, peak_value, color="red", s=70, zorder=3)
                ax.annotate(
                    f"Max: {peak_time:g} s, {peak_value:g} MPa",
                    xy=(peak_time, peak_value),
                    xytext=(20, -25),
                    textcoords="offset points",
                    color="red",
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.85),
                    arrowprops=dict(arrowstyle="->", color="red", linewidth=0.8),
                )
        ax.set_xlabel("Time (s)")
        ax.set_ylabel(ylabel)
        ax.set_axisbelow(True)
        ax.grid(True, color="lightgray", linewidth=0.6, alpha=0.8)
        self.figure.tight_layout()
        self.canvas.draw()


def main():
    app = LoadAnalyzerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
