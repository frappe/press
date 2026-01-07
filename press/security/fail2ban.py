SENSITIVE_PATHS = [
	"admin",
	"awstatstotals",
	"cgi-bin",
	"cms",
	"cpcommerce",
	"db",
	"joomla",
	"muieblackcat",
	"myadmin",
	"mypma",
	"mysql",
	"mysqladmin",
	"mysqldb",
	"phpmyadmin",
	"phpmyadmin1",
	"phpmyadmin2",
	"pma",
	"pmadb",
	"sqladmin",
	"wp-content",
	"wp-includes",
	"wp-login",
	"xampp",
]

RULES = [
	{
		"pattern": '.*"',
		"status_code": "400",
	},
	{
		"pattern": r".*/(" + "|".join(SENSITIVE_PATHS) + r").*",
		"status_code": r"4[\d][\d]",
	},
	{
		"pattern": r".*/picture\?type=normal.*",
		"status_code": r"4[\d][\d]",
	},
	{
		"pattern": r".*/announce.php\?info_hash=.*",
		"status_code": r"4[\d][\d]",
	},
	{
		"pattern": r".*supports_implicit_sdk_logging.*",
		"status_code": r"4[\d][\d]",
	},
	{
		"pattern": r".*activities?advertiser_tracking_enabled.*",
		"status_code": r"4[\d][\d]",
	},
]


def rules() -> str:
	"""
	Get a list of rules to be used in `fail2ban`'s `failregex` configuration.

	:return:
	"""
	return "\n\t".join(map(lambda x: f"<HOST>{x.get('pattern')} {x.get('status_code')}", RULES))
