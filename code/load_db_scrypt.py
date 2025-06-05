from tools import db_load


def main():
    # 定义要传递的参数
    url = "https://feeds.libsyn.com/121695/rss"
    title = "Behind-the-Tech"

    # 调用 db_load.main 函数并传递参数
    db_load.main()


if __name__ == "__main__":
    main()
