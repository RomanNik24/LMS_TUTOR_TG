"""Каталог услуг (docs/05_bot_logic_and_fsm.md, п.3).

До подключения каталога курсов как отдельной сущности в БД (Этап 6+)
услуги отдаются из статического конфига — это осознанная MVP-заглушка:
гость может ознакомиться с предложениями до авторизации.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceItem:
    """Позиция каталога образовательных услуг."""

    title: str
    description: str
    price_hint: str


CATALOG: list[ServiceItem] = [
    ServiceItem(
        title="Индивидуальные занятия по информатике",
        description=(
            "Подготовка к ОГЭ и ЕГЭ, подтягивание школьной программы, "
            "алгоритмы и олимпиадное программирование. Занятия 60–90 мин, "
            "домашние задания с проверкой, записи и конспекты в Mini App."
        ),
        price_hint="от 1500 ₽ / занятие",
    ),
    ServiceItem(
        title="Пробные экзамены с разбором",
        description=(
            "Регулярные пробники в формате ЕГЭ/ОГЭ: автоподсчёт первичного "
            "балла, перевод в отметку 2–5, динамика прогресса в личном кабинете."
        ),
        price_hint="включено в абонемент",
    ),
    ServiceItem(
        title="Групповые мини-группы (2–4 человека)",
        description=(
            "Разбор тем в малых группах, дешевле индивидуального формата. "
            "Расписание и материалы — в приложении."
        ),
        price_hint="от 800 ₽ / занятие",
    ),
]


def render_catalog() -> str:
    """HTML-текст карточки каталога для сообщения бота."""
    lines = ["<b>📚 Каталог курсов и услуг</b>", ""]
    for i, item in enumerate(CATALOG, start=1):
        lines.append(f"<b>{i}. {item.title}</b>")
        lines.append(item.description)
        lines.append(f"<i>{item.price_hint}</i>")
        lines.append("")
    lines.append("Для записи авторизуйтесь командой /login и откройте приложение.")
    return "\n".join(lines).strip()
