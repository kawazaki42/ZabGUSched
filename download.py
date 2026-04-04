import argparse
import pathlib

# import re
from playwright.sync_api import sync_playwright

URL = "https://zabgu.ru/schedule"


def choose(choices: list[str]):
    search_in: list[str] = choices
    idx: int | None = None

    while idx is None:
        for i, x in enumerate(choices):
            print(f"{i}: {x}")

        print("введите номер элемента или текст для поиска")
        i = input("выбор: ")

        filter: str | None = None
        try:
            idx = int(i)
            if idx < 0:
                raise ValueError
        except ValueError:
            filter = i.casefold()
            choices = [x for x in search_in if filter in x.casefold()]

    return choices[idx]


SEARCH_TERMS = dict(
    group="груп",
    lecturer="препод",
    classroom="аудитор",
)

MAY_BE_DISTANT = frozenset({"lecturer", "classroom"})


def get_from_form(by: str, distant: bool = False, show_browser=False):
    search_term: str = SEARCH_TERMS[by]

    # if distant is None and by in MAY_BE_DISTANT:
    #     distant = False

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=not show_browser)
        page = browser.new_page()
        # 451, y'now.
        page.goto(URL, timeout=80_000)

        form = page.locator("form", has_text=search_term)

        select = form.locator("select")
        choices = select.locator("option").all_text_contents()

        opt = choose(choices)
        select.select_option(opt)

        form.get_by_role("button").click()
        page.wait_for_load_state()

        if by in MAY_BE_DISTANT:
            if distant:
                pattern = "заочная форма"
                page.get_by_text(pattern).click()
            else:
                # `Page.get_by_text` searches for substrings and case-insensetively.
                #
                # Need to make sure it doesn't match the opposite choice.
                # pattern = re.compile("(?!за)очная форма", re.IGNORECASE)
                pattern = "очная форма"
                page.get_by_text(pattern).filter(has_not_text="заочная").click()

            page.wait_for_load_state()

        html = page.content()

        if show_browser:
            input("press enter to close...")

        browser.close()
        return opt, html


parser = argparse.ArgumentParser()

# group = parser.add_mutually_exclusive_group(required=True)
# group.add_argument("--group", dest="by", action="store_const", const="груп")
# group.add_argument("--lecturer", dest="by", action="store_const", const="препод")
# group.add_argument("--classroom", dest="by", action="store_const", const="аудитор")

# parser.add_argument("out", type=argparse.FileType("w"), nargs="?")

# args = parser.parse_args()

# with args.out as f:
#     f.write(get_from_form(args.by))


def main(by: str, distant: bool = False, show_browser=False):
    # thx for 451ing.
    print("Please wait...")
    opt, html = get_from_form(
        by,
        distant=distant,
        show_browser=show_browser,
    )

    p = pathlib.Path(f"sources/by_{by}/{opt}.html")

    p.parent.mkdir(parents=True, exist_ok=True)

    p.write_text(html)

    return p


if __name__ == "__main__":
    parser.add_argument(
        "--by", choices=["group", "lecturer", "classroom"], required=True
    )
    parser.add_argument("--show-browser", action="store_true")
    parser.add_argument("--distant", action="store_true")

    args = parser.parse_args()

    main(args.by, args.distant)
