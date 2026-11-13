"""컬럼 설정 창 (T090, FR-027). tkinter(표준 라이브러리)만 쓰고, 판단은 setup_config 함수에 맡긴다.

    python -m trouble_merge.setup_gui --input <폴더 또는 파일...> --config <폴더>

종료 코드: 0 '이 설정으로 통합 실행', 3 '저장만 하고 닫기', 4 취소(창 닫기 포함), 2 설정 오류·예기치 못한 오류.
창은 실제 헤더 이름을 이 PC 화면에만 보인다. 셀 값은 읽지도 보이지도 않는다. 출력은 고정 문구만 낸다.
"""

import argparse
import sys
import warnings
from datetime import datetime

from .mapping import EXTRA_ROLE, FIXED_COLUMNS, STANDARD_COLUMNS, ConfigError
from .setup_config import SaveError, keys_of, save, scan, validate

RUN, SAVE_ONLY, CANCEL, ERROR = 0, 3, 4, 2
OTHER = "기타 항목"


def build_parser():
    parser = argparse.ArgumentParser(prog="trouble_merge.setup_gui")
    parser.add_argument("--input", nargs="+", required=True, help="폴더 또는 파일")
    parser.add_argument("--config", required=True, help="column_map.csv를 저장할 폴더")
    return parser


class SetupWindow:
    def __init__(self, root, result, config_dir):
        import tkinter as tk
        from tkinter import ttk

        self.tk, self.ttk = tk, ttk
        self.root = root
        self.config_dir = config_dir
        self.forms = result.forms
        self.columns = [list(c) for c in result.output_columns]  # [표시 이름, 역할]
        self.exit_code = CANCEL
        self.current = None  # 대응 탭에서 보고 있는 양식

        root.title("컬럼 설정")
        root.geometry("820x560")
        root.protocol("WM_DELETE_WINDOW", self.cancel)

        book = ttk.Notebook(root)
        book.pack(fill="both", expand=True, padx=8, pady=8)
        self.build_forms_tab(book)
        self.build_columns_tab(book)
        self.build_mapping_tab(book)
        book.bind("<<NotebookTabChanged>>", lambda _e: self.refresh_mapping())

        bar = ttk.Frame(root)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="취소", command=self.cancel).pack(side="right")
        ttk.Button(bar, text="저장만 하고 닫기", command=lambda: self.finish(SAVE_ONLY)).pack(side="right", padx=4)
        ttk.Button(bar, text="이 설정으로 통합 실행", command=lambda: self.finish(RUN)).pack(side="right")
        if result.skipped:
            ttk.Label(bar, text="읽지 못한 파일 %d개(형식·크기·열기 실패)" % len(result.skipped)).pack(side="left")

    # ---- ① 양식 찾기 ----
    def build_forms_tab(self, book):
        ttk = self.ttk
        tab = ttk.Frame(book)
        book.add(tab, text="① 양식 찾기")
        self.form_tree = ttk.Treeview(tab, columns=("state", "files", "sheets", "cols"), height=16)
        for key, text, width in (("#0", "양식", 200), ("state", "상태", 160), ("files", "파일 수", 80),
                                 ("sheets", "시트 수", 80), ("cols", "컬럼 수", 80)):
            self.form_tree.heading(key, text=text)
            self.form_tree.column(key, width=width, anchor="w")
        self.form_tree.tag_configure("new", foreground="#b00020")
        self.form_tree.pack(fill="both", expand=True, padx=4, pady=4)
        row = ttk.Frame(tab)
        row.pack(fill="x")
        ttk.Button(row, text="양식 이름 바꾸기", command=self.rename_form).pack(side="left", padx=4)
        ttk.Label(row, text="빨간 줄은 설정에 없는 새 양식입니다. ③ 탭에서 대응을 정하세요.").pack(side="left")
        self.refresh_forms()

    def refresh_forms(self):
        self.form_tree.delete(*self.form_tree.get_children())
        for index, form in enumerate(self.forms):
            state = "새 양식" if form.is_new else form.relation
            self.form_tree.insert("", "end", iid=str(index), text=form.name,
                                  values=(state, form.file_count, form.sheet_count, len(form.headers)),
                                  tags=("new",) if form.is_new else ())

    def rename_form(self):
        from tkinter import messagebox, simpledialog
        selected = self.form_tree.selection()
        if not selected:
            return
        form = self.forms[int(selected[0])]
        name = simpledialog.askstring("양식 이름", "새 이름", initialvalue=form.name, parent=self.root)
        if not name or not name.strip():
            return
        name = name.strip()
        if any(f is not form and f.name == name for f in self.forms):
            messagebox.showerror("양식 이름", "같은 이름의 양식이 이미 있습니다.", parent=self.root)
            return
        form.name = name
        self.refresh_forms()

    # ---- ② 결과 컬럼 ----
    def build_columns_tab(self, book):
        ttk = self.ttk
        tab = ttk.Frame(book)
        book.add(tab, text="② 결과 컬럼")
        self.col_tree = ttk.Treeview(tab, columns=("role",), height=14)
        self.col_tree.heading("#0", text="표시 이름 (통합 시트 순서)")
        self.col_tree.heading("role", text="역할")
        self.col_tree.column("#0", width=300)
        self.col_tree.pack(fill="both", expand=True, padx=4, pady=4)
        row = ttk.Frame(tab)
        row.pack(fill="x")
        for text, command in (("위로", lambda: self.move(-1)), ("아래로", lambda: self.move(1)),
                              ("이름 바꾸기", self.rename_column), ("+ 컬럼 추가", self.add_column),
                              ("추가 컬럼 삭제", self.remove_column)):
            ttk.Button(row, text=text, command=command).pack(side="left", padx=2)
        ttk.Label(tab, text="판정 컬럼 6개는 이름과 순서만 바꿀 수 있습니다. 기타 항목과 원본 정보 컬럼은 항상 맨 뒤에 붙습니다."
                  ).pack(anchor="w", padx=4)
        self.refresh_columns()

    def refresh_columns(self, select=None):
        self.col_tree.delete(*self.col_tree.get_children())
        for index, (name, role) in enumerate(self.columns):
            self.col_tree.insert("", "end", iid=str(index), text=name,
                                 values=("추가 컬럼" if role == EXTRA_ROLE else "판정: " + role,))
        if select is not None:
            self.col_tree.selection_set(str(select))

    def selected_column(self):
        selected = self.col_tree.selection()
        return int(selected[0]) if selected else None

    def move(self, step):
        index = self.selected_column()
        if index is None or not 0 <= index + step < len(self.columns):
            return
        self.columns[index], self.columns[index + step] = self.columns[index + step], self.columns[index]
        self.refresh_columns(index + step)

    def ask_column_name(self, title, initial="", role=EXTRA_ROLE):
        """새 표시 이름. 비었거나 다른 컬럼·고정 컬럼·다른 판정 역할 이름과 같으면 None."""
        from tkinter import messagebox, simpledialog
        name = simpledialog.askstring(title, "표시 이름", initialvalue=initial, parent=self.root)
        if name is None:
            return None
        name = name.strip()
        taken = [c[0] for c in self.columns if c[0] != initial]
        other_role = name in STANDARD_COLUMNS and name != role
        if not name or name in taken or name in FIXED_COLUMNS or other_role:
            messagebox.showerror(title, "비었거나 다른 컬럼·판정 역할과 같은 이름입니다.", parent=self.root)
            return None
        return name

    def rename_column(self):
        index = self.selected_column()
        if index is None:
            return
        old, role = self.columns[index]
        name = self.ask_column_name("이름 바꾸기", old, role)
        if name is None:
            return
        if role == EXTRA_ROLE:
            self.replace_key(old, name)
        self.columns[index][0] = name
        self.refresh_columns(index)

    def add_column(self):
        name = self.ask_column_name("컬럼 추가")
        if name is None:
            return
        self.columns.append([name, EXTRA_ROLE])
        self.refresh_columns(len(self.columns) - 1)

    def remove_column(self):
        index = self.selected_column()
        if index is None or self.columns[index][1] != EXTRA_ROLE:
            return
        self.replace_key(self.columns[index][0], None)
        del self.columns[index]
        self.refresh_columns()

    def replace_key(self, old, new):
        for form in self.forms:
            for header, key in form.mapping.items():
                if key == old:
                    form.mapping[header] = new

    # ---- ③ 양식별 대응 ----
    def build_mapping_tab(self, book):
        tk, ttk = self.tk, self.ttk
        tab = ttk.Frame(book)
        book.add(tab, text="③ 양식별 대응")
        top = ttk.Frame(tab)
        top.pack(fill="x", padx=4, pady=4)
        ttk.Label(top, text="양식").pack(side="left")
        self.form_pick = ttk.Combobox(top, state="readonly", width=30)
        self.form_pick.pack(side="left", padx=4)
        self.form_pick.bind("<<ComboboxSelected>>", lambda _e: self.show_form())
        ttk.Label(tab, text="원본 컬럼마다 결과 컬럼을 고르세요. 고르지 않은 컬럼은 '기타 항목'에 보관됩니다."
                  ).pack(anchor="w", padx=4)
        holder = ttk.Frame(tab)
        holder.pack(fill="both", expand=True)
        canvas = tk.Canvas(holder, highlightthickness=0)
        scroll = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
        self.rows = ttk.Frame(canvas)
        self.rows.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.rows, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def choices(self):
        """콤보 상자에 보일 글자와 키의 대응."""
        shown = [(OTHER, None)]
        for name, role in self.columns:
            key = name if role == EXTRA_ROLE else role
            label = name if role == EXTRA_ROLE or name == role else "%s (%s)" % (name, role)
            shown.append((label, key))
        return shown

    def refresh_mapping(self):
        names = [f.name + (" (새 양식)" if f.is_new else "") for f in self.forms]
        self.form_pick["values"] = names
        if self.forms:
            index = self.forms.index(self.current) if self.current in self.forms else 0
            self.form_pick.current(index)
            self.show_form()

    def show_form(self):
        """고른 양식의 원본 컬럼마다 콤보 상자를 만든다. 고르는 즉시 그 양식의 대응에 기록한다."""
        ttk = self.ttk
        for child in self.rows.winfo_children():
            child.destroy()
        if self.form_pick.current() < 0:
            return
        form = self.forms[self.form_pick.current()]
        self.current = form
        shown = self.choices()
        labels = [label for label, _ in shown]
        for row, header in enumerate(form.headers):
            ttk.Label(self.rows, text=header, width=34).grid(row=row, column=0, sticky="w", padx=4, pady=1)
            combo = ttk.Combobox(self.rows, state="readonly", values=labels, width=30)
            key = form.mapping.get(header)
            combo.current(next((i for i, (_, k) in enumerate(shown) if k == key), 0))
            combo.bind("<<ComboboxSelected>>",
                       lambda _e, h=header, c=combo, s=shown: form.mapping.__setitem__(h, s[c.current()][1]))
            combo.grid(row=row, column=1, sticky="w", padx=4, pady=1)

    # ---- 저장 ----
    def finish(self, code):
        from tkinter import messagebox
        allowed = set(keys_of([tuple(c) for c in self.columns]))
        for form in self.forms:  # 지운 추가 컬럼을 가리키는 대응은 기타 항목으로
            for header, key in form.mapping.items():
                if key is not None and key not in allowed:
                    form.mapping[header] = None
        errors, warns = validate([(f.name, f.mapping) for f in self.forms])
        if errors:
            lines = ["%s: '%s'에 %s" % (name, key, ", ".join(headers)) for name, key, headers in errors]
            messagebox.showerror("저장할 수 없음", "한 양식에서 같은 결과 컬럼을 두 번 골랐습니다.\n\n"
                                 + "\n".join(lines), parent=self.root)
            return
        if warns:
            lines = ["%s: %s 없음" % (name, ", ".join(missing)) for name, missing in warns]
            if not messagebox.askyesno("확인", "다음 양식은 필수 컬럼 대응이 없어 행이 '확인 필요'가 됩니다.\n\n"
                                       + "\n".join(lines) + "\n\n그래도 저장할까요?", parent=self.root):
                return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            save(self.config_dir, [(f.name, f.header_row, f.sheet, f.mapping) for f in self.forms],
                 [tuple(c) for c in self.columns], stamp)
        except SaveError as error:
            messagebox.showerror("저장할 수 없음", str(error), parent=self.root)
            return
        except OSError:
            messagebox.showerror("저장할 수 없음", "설정 폴더에 쓸 수 없습니다.", parent=self.root)
            return
        self.exit_code = code
        self.root.destroy()

    def cancel(self):
        self.exit_code = CANCEL
        self.root.destroy()


def main(argv=None):
    warnings.simplefilter("ignore")
    args = build_parser().parse_args(argv)
    try:
        result = scan(args.input, args.config)
    except ConfigError as error:
        print("설정 오류: %s" % error, file=sys.stderr)
        return ERROR
    except Exception:  # 메시지와 종류를 모두 버리고 고정 문구만 낸다
        print("처리 중 예기치 못한 오류", file=sys.stderr)
        return ERROR
    try:
        import tkinter as tk
        root = tk.Tk()
        window = SetupWindow(root, result, args.config)
        root.mainloop()
        return window.exit_code
    except Exception:
        print("설정 창을 열 수 없음", file=sys.stderr)
        return ERROR


if __name__ == "__main__":
    sys.exit(main())
