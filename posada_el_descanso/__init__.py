# PyMySQL permite usar MySQL sin compilar mysqlclient en Windows.
# Django lo reconocerá como si fuera MySQLdb.
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass
