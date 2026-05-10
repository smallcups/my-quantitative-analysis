import tushare as ts
import pymysql

class DatabaseUtils:
    # 数据库连接信息
    _host = 'localhost'       # 替换为你的MySQL主机 118.31.12.34
    _user = 'root'   # 替换为你的MySQL用户名
    _password = '123456'  # 替换为你的MySQL密码
    _database = 'stock_cursor'  # 替换为你的MySQL数据库名
    _charset = 'utf8mb4'

    # Tushare API token
    _tushare_token = '855c47d0b83872b7b31bc31e6b4dec6c77fbcebcda4257af6c191253'

    @classmethod
    def init_tushare_api(cls):
        """
        初始化Tushare API
        :return: Tushare pro API对象
        """
        return ts.pro_api(cls._tushare_token)

    @classmethod
    def connect_to_mysql(cls):
        """
        连接到MySQL数据库
        :return: MySQL连接对象和游标
        """
        conn = pymysql.connect(
            host=cls._host,
            user=cls._user,
            password=cls._password,
            database=cls._database,
            charset=cls._charset
        )
        cursor = conn.cursor()
        return conn, cursor 