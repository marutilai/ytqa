import browser_cookie3
import time


def get_youtube_cookies():
    try:
        # Try to get cookies from Chrome first
        cookies = browser_cookie3.chrome(domain_name=".youtube.com")
    except:
        try:
            # Fall back to Firefox if Chrome fails
            cookies = browser_cookie3.firefox(domain_name=".youtube.com")
        except:
            print("Could not find cookies from Chrome or Firefox")
            return

    with open("cookies.txt", "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# https://www.youtube.com\n")
        f.write(f"# Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for cookie in cookies:
            # Only save essential YouTube cookies
            if any(
                name in cookie.name
                for name in [
                    "VISITOR_INFO1_LIVE",
                    "LOGIN_INFO",
                    "SID",
                    "__Secure-1PSID",
                    "HSID",
                    "SSID",
                    "APISID",
                    "SAPISID",
                ]
            ):
                f.write(
                    f"{cookie.domain}\tTRUE\t{cookie.path}\t"
                    f"{'TRUE' if cookie.secure else 'FALSE'}\t{cookie.expires}\t"
                    f"{cookie.name}\t{cookie.value}\n"
                )

    print("Cookies have been saved to cookies.txt")


if __name__ == "__main__":
    get_youtube_cookies()
