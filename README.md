# Slack Bot WRSS Ping

Bot na komunikator Slack służący do analizowania reakcji do danej wiadomości, czyli WRSS'owego "głosowania"

## Funkcjonalności

-   Analiza reakcji do wiadomości
-   Wyświetlanie statystyk
-   Wyświetlanie listy osób, które zagłosowały, które nie zagłosowały
-   Wysyłanie wiadomości do osób, które nie zagłosowały
-   Dodawanie wiadomości na kanale

# Instrukcje dla WRSS

## Jak dołączyć bota do kanału

1. W górnym pasku wchodzimy w szczegóły kanału (klikamy na nazwę)
2. Wchodzimy w zakładkę **Integrations**
3. Klikamy **Add an app**
4. W okienku znaleźć **WRSS Ping**

Można korzystać z bota na tym kanale

## Jak uruchomić bota

1. Zainstalować Pythona [tutaj](https://www.python.org/downloads/)
2. Do uruchomienia programu potrzebne są biblioteki, które instaluje się w poniższy sposób\*:
    - `pip install python-dotenv` - służy do korzystania z lokalnych zmiennych środowiskowych
    - `pip install slack_bolt` - API Slack'owe
3. Pobrać program `bot.py` z tego repozytorium lub przekleić kod źródłowy
4. Należy pobrać plik `.env` z [Google Drive](https://drive.google.com/file/d/1wh4t1ot8eTmazeOLzbVowRuljoq7WX_S/view?usp=sharing) - **plik `.env` i `bot.py` muszą być w jednym folderze**
5. Należy uruchomić program: `python bot.py`

    > \*komendy mogą przybierać formę `pip3` i `python3` w zależności od OS i wersji Python

## Jak korzystać z bota?

Wchodzimy w ... (opcje) wybranej wiadomości, powinien być widoczny program **Analizuj reakcje**.  
 Gdy go nie widać klikamy **More message shortcuts...** i tam z pewnością będzie ;)

# Miłego korzystania, w razie problemów piszcie/zgłaszajcie bugi :D
