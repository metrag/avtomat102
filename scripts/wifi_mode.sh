#!/bin/bash
# Переключение ПК между домашней сетью (интернет) и боевой сетью тренажёра AKK.
#
#   scripts/wifi_mode.sh akk   — ПК и плата в AKK (без интернета) — боевой тест;
#   scripts/wifi_mode.sh home  — ПК обратно в MALAH_5G (интернет).
#
# NetworkManager при отсутствии интернета в AKK сам возвращается в домашнюю сеть,
# поэтому здесь autoconnect домашних сетей выключается. Вернуться — этой же
# командой с аргументом home.

set -u

MODE="${1:-}"

case "$MODE" in
    akk)
        nmcli connection modify "MALAH_5G" connection.autoconnect no >/dev/null 2>&1
        nmcli connection modify "MALAH" connection.autoconnect no >/dev/null 2>&1
        if ! nmcli -t -f NAME connection show | grep -qx "AKK"; then
            nmcli device wifi connect "AKK" password "00000000" >/dev/null
        fi
        # Фиксированный адрес ПК: плата шлёт фото unicast-ом на 192.168.0.217
        # (WiFi broadcast идёт без ACK и повторов — кадры терялись).
        # powersave off: иначе кадры задерживаются в буфере точки доступа.
        nmcli connection modify "AKK" ipv4.method manual ipv4.addresses 192.168.0.217/24 ipv4.gateway "" 802-11-wireless.powersave 2 >/dev/null 2>&1
        nmcli connection up AKK
        ;;
    home)
        nmcli connection modify "AKK" connection.autoconnect no >/dev/null 2>&1
        nmcli connection modify "MALAH_5G" connection.autoconnect yes >/dev/null 2>&1
        nmcli connection up MALAH_5G
        ;;
    *)
        echo "Использование: $0 akk|home"
        exit 1
        ;;
esac

echo "Текущая сеть:"
nmcli -t -f ACTIVE,SSID dev wifi
ip -4 route | head -n 1
