import argparse
import logging
import pathlib

# import re
from playwright.sync_api import sync_playwright

URL = "https://zabgu.ru/schedule"


logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)


def choose_noninteractive(choices: list[str], pattern: str) -> str:
    choices = [elem for elem in choices if pattern.casefold() in elem.casefold()]

    if len(choices) != 1:
        raise ValueError("not unique!")

    return choices[0]


def choose_interactive(choices: list[str]) -> str:
    search_in: list[str] = choices
    idx: int | None = None

    while idx is None:
        for i, x in enumerate(choices):
            print(f"{i}: {x}")

        print("введите номер элемента или текст для поиска")
        c = input("выбор: ")

        pattern: str | None = None
        try:
            idx = int(c)
            if idx < 0:
                raise ValueError
        except ValueError:
            pattern = c.casefold()
            choices = [elem for elem in search_in if pattern in elem.casefold()]

    return choices[idx]


SEARCH_TERMS = dict(
    group="груп",
    lecturer="препод",
    classroom="аудитор",
)

MAY_BE_DISTANT = frozenset({"lecturer", "classroom"})


def get_from_form(
    by: str,
    distant: bool = False,
    show_browser=False,
    search_term: str | None = None,
):
    form_search_term = SEARCH_TERMS[by]

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=not show_browser)
        page = browser.new_page()
        # 451, y'now.
        # page.goto(URL, timeout=90_000)
        page.goto(URL, wait_until="domcontentloaded")

        form = page.locator("form", has_text=form_search_term)

        select = form.locator("select")
        choices = select.locator("option").all_text_contents()

        if search_term is None:
            opt = choose_interactive(choices)
        else:
            opt = choose_noninteractive(choices, search_term)

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
                pattern = "очная форма"
                page.get_by_text(pattern).filter(has_not_text="заочная").click()

            page.wait_for_load_state()

        html = page.content()

        # if show_browser:
        #     input("press enter to close...")

        browser.close()
        return opt, html


parser = argparse.ArgumentParser()


def main(
    by: str, distant: bool = False, *, search_term=None, show_browser=False
) -> tuple[str, pathlib.Path]:
    # thx for 451ing.
    logger.info("getting data from webpage")
    opt, html = get_from_form(
        by,
        distant=distant,
        show_browser=show_browser,
        search_term=search_term,
    )

    p = pathlib.Path(f"sources/by_{by}/{opt}.html")

    p.parent.mkdir(parents=True, exist_ok=True)

    p.write_text(html)

    return opt, p
