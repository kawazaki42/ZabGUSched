# import collections.abc
# import sys
# from pprint import pprint
import contextlib
import itertools
import logging
import math
import os
import re
import textwrap
from pathlib import Path

import pandas as pd
from tabulate import tabulate


class Sched:
    def __init__(self, target, input_path=None):
        self.target = target
        if input_path is not None:
            self.input_path = input_path

    headers: list | None = None
    drop = []

    input_path: str | os.PathLike = "sources"

    translate_headers = dict(
        nlecture="№",
        group="группа",
        subgroup="п/гр",
        discipline="предмет",
        lecture_kind="тип занятия",
        lecturer="преподаватель",
        department="кафедра",
        classroom="аудитория",
    )

    _raw = None

    @property
    def raw(self):
        if self._raw is not None:
            return self._raw

        tables = []

        p = Path(self.input_path)
        if p.is_dir():
            files = p.iterdir()
        else:
            files = [p]

        for file in files:
            if not file.is_file():
                continue

            table = pd.read_html(file, flavor="html5lib", header=0)[0]

            tables.append(table)

        self._raw = pd.concat(tables)

        # normalize integer ids
        self._raw.reset_index(inplace=True, drop=True)

        assert self.headers is not None

        if len(self._raw.columns) != len(self.headers):
            logger.warning("table structure might have been changed")

        # set internal names instead of displayed ones
        self._raw.columns = self.headers

        # print(self._raw, file=sys.stderr)

        return self._raw

    wkday_names = [
        "понедельник",
        "вторник",
        "среда",
        "четверг",
        "пятница",
        "суббота",
        "воскресенье",
    ]

    month_names = [
        "январь",
        "февраль",
        "март",
        "апрель",
        "май",
        "июнь",
        "июль",
        "август",
        "сентябрь",
        "октябрь",
        "декабрь",
    ]

    date_regex = re.compile(r"\s*(\d+)\s*(\w+)\s*")

    @classmethod
    def day_cmp_key(cls, day: str):
        try:
            return cls.wkday_names.index(day.strip())
        except ValueError:
            pass

        if match := cls.date_regex.fullmatch(day):
            n, maybe_month = match.groups()

            n = int(n)

            for i, name in cls.month_names:
                if name.startswith(maybe_month.lower()):
                    return (maybe_month, n)

        # shouldn't happen
        return day

    def by_day(self):
        g = self.raw.groupby("day", sort=False)
        # i: collections.abc.Iterator[tuple[str, pd.DataFrame]] = iter(g)
        return sorted(g, key=lambda kv: self.day_cmp_key(str(kv[0])))

    def _format_day(self, dname, leclist: pd.DataFrame | None) -> str:
        pat = """\
        ### {dname}

        {table}

        """

        pat = textwrap.dedent(pat)

        if leclist is None:
            return pat.format(dname=dname, table="пусто")

        assert self.drop is not None
        assert self.headers is not None

        drop = self.drop + ["day", "week"]
        headers = [elem for elem in self.headers if elem not in drop]

        reclist = (
            leclist.drop(columns=drop).dropna(subset="discipline").to_dict("records")
        )

        g = itertools.groupby(reclist, key=lambda rec: rec["nlecture"])

        # reclist.sort(key=lambda rec: rec["nlecture"])

        # new_reclist = {}
        # for rec in reclist:
        #     n = rec["nlecture"]
        #     new_rec = {}
        #     new_reclist[n] = new_rec
        #     for k, v in rec.items():
        #         new_rec[k] = v

        # for i in range(6):
        #     new_reclist.setdefault(i + 1, dict(nlecture=i + 1, discipline="пусто"))

        # new_reclist = [new_reclist[i + 1] for i in range(6)]

        grouped = {n: list(recs) for n, recs in g}

        defaults = dict.fromkeys(headers)
        defaults.update(discipline="пусто")

        new_reclist = []

        for zi in range(8):
            oi = zi + 1
            recs = grouped.get(oi, [defaults | dict(nlecture=oi)])

            recs.sort(key=lambda rec: rec["subgroup"])

            for r in recs:
                match r["subgroup"]:
                    case float(f) if math.isnan(f):
                        r["subgroup"] = None

            new_reclist.extend(recs)

        new_reclist = [
            {self.translate_headers[k]: v for k, v in d.items()} for d in new_reclist
        ]

        logger.debug(new_reclist)
        table = tabulate(
            new_reclist,
            tablefmt="github",
            # headers={elem: elem for elem in headers},
            headers="keys",
            showindex=False,
        )

        return pat.format(
            dname=dname,
            table=table,
        )

    def _target_marker(self) -> str:
        pat = """\
        {target}
        ===

        """
        return textwrap.dedent(pat).format(target=self.target)

    def dump(self, path="output") -> None:
        with (
            open(Path(path) / "sched.md", "w", encoding="utf8") as f,
            contextlib.redirect_stdout(f),
        ):
            print(self._target_marker())
            for dname, day in self.by_day():
                print(self._format_day(dname, day))


class WeekSeparatedSched(Sched):
    week_filename = {
        "в": "upper",
        "н": "lower",
    }

    week_filename_invert = dict(
        в="lower",
        н="upper",
    )

    week_fullname = dict(
        в="верхняя неделя",
        н="нижняя неделя",
    )

    def by_week(self):
        for dname, day in self.by_day():
            yield dname, dict(list(day.groupby("week", sort=False)))

    def _print_one_week(self, week_code, prefix=""):
        print(prefix)

        for dname, day in self.by_week():
            leclist = day.get(week_code)
            print(self._format_day(dname, leclist))

    def dump(self, path="output"):
        prefix = """\
        {target}{header}
        ---

        [Другая неделя]({invert_link})

        """

        prefix = textwrap.dedent(prefix)

        path = Path(path)

        with (
            open(path / "upper.md", "w", encoding="utf8") as f,
            contextlib.redirect_stdout(f),
        ):
            self._print_one_week(
                "в",
                prefix.format(
                    header=self.week_fullname["в"].capitalize(),
                    invert_link=self.week_filename_invert["в"] + ".md",
                    target=self._target_marker(),
                ),
            )

        with (
            open(path / "lower.md", "w", encoding="utf8") as f,
            contextlib.redirect_stdout(f),
        ):
            self._print_one_week(
                "н",
                prefix.format(
                    header=self.week_fullname["н"].capitalize(),
                    invert_link=self.week_filename_invert["н"] + ".md",
                    target=self._target_marker(),
                ),
            )


class SchedByGroup(WeekSeparatedSched):
    input_path = "sources/by_group"

    headers = [
        "day",
        "nlecture",
        "week",
        "subgroup",
        # 'subject',
        "discipline",
        "lecture_kind",
        "lecturer",
        # 'chair',
        "department",
        # 'auditorium',
        "classroom",
    ]

    drop = [
        "lecturer",
        "department",
    ]


class SchedByGroupDistant(Sched):
    input_path = "sources/by_group"

    headers = [
        "day",
        "nlecture",
        # "week", # NOTE
        "group",
        "discipline",
        "lecture_kind",
        "lecturer",
        "department",
        "classroom",
    ]


class SchedByLecturer(WeekSeparatedSched):
    input_path = "sources/by_lecturer"

    headers = [
        "day",
        "nlecture",
        "week",
        "subgroup",
        "group",
        "discipline",
        "lecture_kind",
        "lecturer",
        "department",
        "classroom",
    ]

    drop = [
        "lecturer",
        "department",
    ]


class SchedByLecturerDistant(Sched):
    input_path = "sources/by_lecturer"

    headers = [
        "day",
        "nlecture",
        # "week", # NOTE
        "group",
        "discipline",
        "lecture_kind",
        "lecturer",
        "department",
        "classroom",
    ]

    drop = [
        "lecturer",
        "department",
    ]


class SchedByClassroom(WeekSeparatedSched):
    input_path = "sources/by_classroom"

    headers = [
        "day",
        "nlecture",
        "week",
        "subgroup",
        "group",
        "discipline",
        "lecture_kind",
        "lecturer",
        "department",
        "classroom",
    ]

    # browse multiple at once?

    # drop = [
    #     "classroom",
    # ]


class SchedByClassroomDistant(Sched):
    input_path = "sources/by_classroom"

    headers = [
        "day",
        "nlecture",
        # "week", # NOTE
        "group",
        "discipline",
        "lecture_kind",
        "lecturer",
        "department",
        "classroom",
    ]


CLASSES = {
    "group": (SchedByGroup, SchedByGroupDistant),
    "lecturer": (SchedByLecturer, SchedByLecturerDistant),
    "classroom": (SchedByClassroom, SchedByClassroomDistant),
}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="download and format schedule from university's website"
    )

    group = parser.add_argument_group("schedule kind")

    group.add_argument(
        "--by",
        choices=["group", "lecturer", "classroom"],
        required=True,
        help="schedule type to format",
    )

    group.add_argument(
        "--distant", action="store_true", help="work with extramural students' schedule"
    )

    parser.add_argument(
        "--target",
        help="a case-insensitive pattern for a group, lecturer or classroom."
        + "\nIf not unique, exit with nonzero status."
        + " If not given, opens interactive choice.",
    )

    parser.add_argument(
        "--offline", action="store_true", help="use locally downloaded HTML pages [WIP]"
    )

    parser.add_argument(
        "-o",
        "--output",
        # default="output",
        help="directory to write output to (created if doesn't exist)",
    )

    group = parser.add_argument_group("debug")

    group.add_argument(
        "--show-browser",
        action="store_true",
        help="show embedded browser window when getting data from website",
    )

    group.add_argument(
        "-v", "--verbose", action="store_true", help="set log level to DEBUG"
    )

    # parser.add_argument("--fetch", action="store_true")

    args = parser.parse_args()

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    # classes = dict(
    #     group=SchedByGroup,
    #     lecturer=SchedByLecturer,
    #     classroom=SchedByClassroom,
    # )

    # cls = classes[args.by]

    # full_target = None
    # html_path = None
    # if args.fetch:
    if not args.offline:
        import download

        full_target, html_path = download.main(
            args.by,
            args.distant,
            search_term=args.target,
            show_browser=args.show_browser,
        )
    else:
        # TODO: glob escape
        g = (
            Path("sources")
            .joinpath(f"by_{args.by}")
            .glob(f"*{args.target}*", case_sensitive=False)
        )
        # g = list(g)
        # if len(g) != 1:
        #     raise ValueError
        # html_path = g[0]

        match list(g):
            case [x]:
                html_path = x
                full_target = x.stem
            case []:
                raise RuntimeError("no local data source found")
            case [*_]:
                raise RuntimeError("source file not unique")
            case _:
                raise TypeError

    # cls = None
    # match args.by:
    #     case "group":
    #         cls = SchedByGroup if not args.distant else SchedByGroupDistant
    #     case "lecturer":
    #         cls = SchedByLecturer if not args.distant else SchedByLecturerDistant
    #     case "classroom":
    #         cls = SchedByClassroom if not args.distant else SchedByClassroomDistant
    #     case _:
    #         raise ValueError

    cls = CLASSES[args.by][1 if args.distant else 0]

    if args.output is None and full_target is not None:
        args.output = Path(f"output/by_{args.by}/{full_target}")
        args.output.mkdir(parents=True, exist_ok=True)

    assert html_path is not None
    inst = cls(target=full_target, input_path=html_path)
    # if path:
    #     inst.input_path = path
    inst.dump(args.output)
