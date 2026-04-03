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
        except ValueError:
            filter = i.lower()
            choices = [x for x in search_in if filter in x.lower()]

    return choices[idx]


def get_from_form(search_term: str):
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        page = browser.new_page()
        page.goto(URL, timeout=80_000)

        # page.get_by_text()
        form = page.locator("form", has_text=search_term)
        # select = page.locator("#type_group")
        select = form.locator("select")
        choices = select.locator("option").all_text_contents()
        # print(choices)
        o = choose(choices)
        select.select_option(o)
        # form.locator("input")
        form.get_by_role("button").click()
        page.wait_for_load_state()

        return o, page.content()

        # browser.close()
        input("press to close...")


import argparse
import pathlib

parser = argparse.ArgumentParser()

# group = parser.add_mutually_exclusive_group(required=True)
# group.add_argument("--group", dest="by", action="store_const", const="груп")
# group.add_argument("--lecturer", dest="by", action="store_const", const="препод")
# group.add_argument("--classroom", dest="by", action="store_const", const="аудитор")

# parser.add_argument("out", type=argparse.FileType("w"), nargs="?")

# args = parser.parse_args()

# with args.out as f:
#     f.write(get_from_form(args.by))

parser.add_argument("--by", choices=["group", "lecturer", "classroom"], required=True)
args = parser.parse_args()

search_terms = dict(
    group="груп",
    lecturer="препод",
    classroom="аудитор",
)

print("this may take a while...")
opt, html = get_from_form(search_terms[args.by])

p = pathlib.Path(f"sources/by_{args.by}/{opt}.html")

p.parent.mkdir(parents=True, exist_ok=True)

p.write_text(html)
