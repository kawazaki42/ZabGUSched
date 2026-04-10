> ```sh
> $ python -m this | head -1
> The Zen of Python, by Tim Peters
> $ python -m this | grep purity
> Although practicality beats purity.
> ```

## TODO

- [x] поиск в CLI
- [ ] задать имя выходного файла
  - [x] сортировать входные и выходные файлы по папкам
- [x] описание внутри файла
- [x] баг с подргуппами!
- [x] порядок столбцов
- [x] `nan` вместо пустой ячейки

# Установка через `uv`

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
# Установить браузер для работы с формами на сайте.
# `playwright` не использует уже установленнй в системе браузер.
playwright install firefox
```

# Использование

Справка генерируется через `argparse` и доступна по команде:

```sh
python mksched.py --help
```

> [!TODO]
> локализация

## Примеры

**Скачать и форматировать раписание группы очников**

```sh
python mksched.py --by group --target 'ивт-24'
```

- Поиск ведется по подстроке и нечувствителен к регистру
- Загрузит страницу с сайта в файл `./sources/by_group/ИВТ-24-1.html`
- Результат форматирования: `./output/by_group/ИВТ-24-1/{upper,lower}.md`
