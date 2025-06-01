import itertools
import json
import re
import phonenumbers

from phonenumbers import PhoneNumberMatcher, PhoneNumberFormat

from typing import Iterable, Tuple, Set, Mapping, Any

EMAIL_RE = re.compile(
    r'''(?<![\w@.+-])                       
        [\w.+-]{1,64}                       
        @                                    
        (?:[\w-]{1,63}\.)+                  
        [A-Za-z]{2,63}                      
    (?![\w@.+-])                             
    ''',
    re.X | re.U
)
DIGITS = re.compile(r"\D+")
FMT = PhoneNumberFormat.E164

MOBILE_RE = re.compile(r'^\+79\d{9}$')      # мобильные: +7 9XXXXXXXXX
LANDLINE_RE = re.compile(r'^\+74\d{9}$')

def extract_phones_any(payload, default_region="RU"):
    """
    ▸ Не зависит от названий полей;
    ▸ Отсекает ИНН/ОГРН и прочие «голые» цифровые строки;
    ▸ Возвращает уникальные телефоны в E.164.
    """
    whole_text = json.dumps(payload, ensure_ascii=False)

    phones = set()
    for m in PhoneNumberMatcher(whole_text, default_region):
        raw = whole_text[m.start:m.end]
        digits_only = DIGITS.sub('', raw)

        looks_like_phone = (
            '+' in raw
            or any(ch in raw for ch in '()- ')
            or len(digits_only) >= 11
        )
        if not looks_like_phone:
            continue

        num_obj = m.number
        if not (phonenumbers.is_possible_number(num_obj)
                and phonenumbers.is_valid_number(num_obj)):
            continue

        formatted = phonenumbers.format_number(num_obj, FMT)
        # Пропускаем все стационарные +74…
        if LANDLINE_RE.match(formatted):
            continue

        # (Опционально) убеждаемся, что это именно мобильный +79…
        if not MOBILE_RE.match(formatted):
            continue

        phones.add(formatted)

        if len(phones) >= 10:
            break

    return sorted(phones)


def extract_emails_any(payload) -> list[str]:
    blob = json.dumps(payload, ensure_ascii=False)
    return sorted({m.group(0).lower() for m in EMAIL_RE.finditer(blob)})


def collect_contacts(payloads: Iterable[Mapping[str, Any]]
                     ) -> Tuple[Set[str], Set[str]]:

    phones: Set[str]  = set()
    emails: Set[str]  = set()

    for p in payloads:
        phones.update(extract_phones_any(p))
        emails.update(extract_emails_any(p))

    return phones, emails