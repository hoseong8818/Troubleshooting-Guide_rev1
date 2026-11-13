"""T083: 표시 이름을 바꾼 통합 엑셀로도 게시판 데이터가 같다 (FR-026).

게시판은 통합 엑셀의 '컬럼 역할' 시트로 역할을 찾아, 표시 이름과 상관없이 지금과 같은 게시글을 만든다.
"""

import unittest

from tests.support import CONFIG, CliCase, make_config, read_sheet, result_files, run_cli
from tests.test_board import posts_of, run_board
from tests.test_output_columns import INPUTS, RENAMED, write_output_columns


class BoardRolesTest(CliCase):
    def board_posts(self, config, name):
        out = self.tmp / name
        result = run_cli(INPUTS, config, out)
        self.assertEqual(result.returncode, 0, "stderr: " + result.stderr[-300:])
        merged = result_files(out)[0]
        self.first_header = read_sheet(merged)[0][0]
        board_out = self.tmp / (name + "_board")
        result = run_board(merged, board_out)
        self.assertEqual(result.returncode, 0, result.stderr[-300:])
        return posts_of((board_out / "board.html").read_text(encoding="utf-8"))

    def test_renamed_columns_give_the_same_posts(self):
        base = self.board_posts(CONFIG, "base")
        config = make_config(self.tmp, ())
        write_output_columns(config, RENAMED)
        renamed = self.board_posts(config, "renamed")
        self.assertEqual(self.first_header, "호기", "통합 시트 헤더가 표시 이름으로 바뀌지 않았다")
        self.assertEqual(len(renamed), len(base))
        self.assertEqual(renamed, base)


if __name__ == "__main__":
    unittest.main()
