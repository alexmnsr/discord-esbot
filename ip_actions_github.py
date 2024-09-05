import subprocess
import requests
import json


def fetch_github_actions_ips():
    url = "https://api.github.com/meta"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get('actions', [])
    else:
        print("Failed to fetch IP addresses from GitHub.")
        return []


def add_ip_to_ufw(ip):
    try:
        # Формируем команду для добавления IP-адреса в ufw
        command = f"sudo ipset add github-actions {ip} "
        # Выполняем команду
        subprocess.run(command, shell=True, check=True)
        print(f"Added {ip} to UFW rules.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to add {ip} to UFW rules: {e}")


def main():
    # Получаем список IP-адресов для GitHub Actions
    ips = fetch_github_actions_ips()
    if not ips:
        print("No IP addresses to add.")
        return

    print(f"Adding {len(ips)} IP addresses to UFW...")

    for ip in ips:
        add_ip_to_ufw(ip)

    # Применяем изменения в UFW
    try:
        subprocess.run("sudo ufw reload", shell=True, check=True)
        print("UFW rules reloaded.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to reload UFW rules: {e}")


if __name__ == "__main__":
    main()
