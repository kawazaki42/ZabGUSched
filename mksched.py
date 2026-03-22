import contextlib
import pathlib
import re
import sys
import textwrap
from pprint import pprint

import pandas as pd
from tabulate import tabulate


class Sched:
    drop = []

    input_path = "sources"

    _raw = None

    @property
    def raw(self):
        if self._raw is not None:
            return self._raw

        tables = []

        for file in pathlib.Path(self.input_path).iterdir():
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


class WeekSeparated(Sched):
    week_labels = {
        "в": "upper",
        "н": "lower",
    }

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
                    header=wkdisplay["в"].capitalize(),
                    invert_link=invert["в"] + ".md",
                ),
            )

        with (
            open("lower.md", "w", encoding="utf8") as f,
            contextlib.redirect_stdout(f),
        ):
            self._print_one_week(
                "н",
                prefix.format(
                    header=wkdisplay["н"].capitalize(),
                    invert_link=invert["н"] + ".md",
                ),
            )


class SchedByGroup(WeekSeparated):
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


class SchedByLecturer(WeekSeparated):
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


class SchedByClassroom(Sched):
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

    drop = [
        "classroom",
    ]


headermap = dict(
    nlecture="№",
    group="группа",
    subgroup="п/гр",
    discipline="предмет",
    lecture_kind="тип занятия",
    lecturer="преподаватель",
    department="кафедра",
    classroom="аудитория",
)

wkdisplay = dict(
    в="верхняя неделя",
    н="нижняя неделя",
)

invert = dict(
    в="lower",
    н="upper",
)

SchedByLecturer().dump()
