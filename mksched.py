import contextlib
import os
import pathlib
import re
import sys
import textwrap
from pprint import pprint

import pandas as pd
from tabulate import tabulate


class Sched:
    headers = []
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

        p = pathlib.Path(self.input_path)
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

        if len(self._raw.columns) != len(self.headers):
            print("Warning: table structure might have been changed!", file=sys.stderr)

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
        return sorted(
            self.raw.groupby("day", sort=False), key=lambda kv: self.day_cmp_key(kv[0])
        )

    def _format_day(self, dname, leclist: pd.DataFrame):
        reclist = (
            leclist.drop(columns=self.drop + ["day", "week"])
            .dropna(subset="discipline")
            .to_dict("records")
        )

        new_reclist = {}
        for rec in reclist:
            n = rec["nlecture"]
            new_rec = {}
            new_reclist[n] = new_rec
            for k, v in rec.items():
                new_rec[k] = v

        for i in range(6):
            new_reclist.setdefault(i + 1, dict(nlecture=i + 1, discipline="пусто"))

        new_reclist = [new_reclist[i + 1] for i in range(6)]
        new_reclist = [
            {self.translate_headers[k]: v for k, v in d.items()} for d in new_reclist
        ]
        # TODO: translate

        pprint(new_reclist, stream=sys.stderr)
        table = tabulate(
            new_reclist,
            tablefmt="github",
            headers="keys",
            showindex=False,
        )
        return textwrap.dedent(
            """
            {dname}
            ---

            {table}

            """[1:]
        ).format(
            dname=dname,
            table=table,
        )

    def dump(self):
        with (
            open("sched.md", "w", encoding="utf8") as f,
            contextlib.redirect_stdout(f),
        ):
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
            leclist = day[week_code]
            print(self._format_day(dname, leclist))

    def dump(self):
        prefix = textwrap.dedent(
            """
            {header}
            ===

            [Другая неделя]({invert_link})

            """[1:]
        )

        with (
            open("upper.md", "w", encoding="utf8") as f,
            contextlib.redirect_stdout(f),
        ):
            self._print_one_week(
                "в",
                prefix.format(
                    header=self.week_fullname["в"].capitalize(),
                    invert_link=self.week_filename_invert["в"] + ".md",
                ),
            )

        with (
            open("lower.md", "w", encoding="utf8") as f,
            contextlib.redirect_stdout(f),
        ):
            self._print_one_week(
                "н",
                prefix.format(
                    header=self.week_fullname["н"].capitalize(),
                    invert_link=self.week_filename_invert["н"] + ".md",
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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--by", choices=["group", "lecturer", "classroom"], required=True
    )
    parser.add_argument("--distant", action="store_true")
    parser.add_argument("--fetch", action="store_true")

    args = parser.parse_args()

    # classes = dict(
    #     group=SchedByGroup,
    #     lecturer=SchedByLecturer,
    #     classroom=SchedByClassroom,
    # )

    # cls = classes[args.by]

    path = None
    if args.fetch:
        import download

        path = download.main(args.by, args.distant)

    cls = None
    match args.by:
        case "group":
            cls = SchedByGroup if not args.distant else SchedByGroupDistant
        case "lecturer":
            cls = SchedByLecturer if not args.distant else SchedByLecturerDistant
        case "classroom":
            cls = SchedByClassroom if not args.distant else SchedByClassroomDistant
        case _:
            raise ValueError

    inst = cls()
    if path:
        inst.input_path = path
    inst.dump()
