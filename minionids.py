import getpass
import os
import sys
from typing import Dict

import logger as _logger
from globals import Maint
from logger import logger
from sqlmanager import Database


def load_minionids() -> Dict[str, str]:
	minion_sql = Database.select('minions', ('id', 'name'))  # from the FTS database, select `id` and `name` from the `minions` table
	# from [{'id': '058', 'name': 'dave'}] -> {'daveminion': '058'}
	minions = {d['name'] + "minion": d['id'] for d in minion_sql}
	return minions


def load_minion_config(*, skip_maint_load=False):
	"""
	Load the minion ids and the configuration necessary to run the miosk.
	This includes:

	- miosk name (computername)
	- miosk id
	- checking for spoofed minion in args
	- loading the config file
	- load the polynomials

	:param skip_maint_load: skips the config file and polynomial loading
	"""
	minions = load_minionids()
	Maint.computername = getpass.getuser().replace(".", "").lower()  # e.g. dave.minion -> daveminion, phil.minion -> philminion
	# check for a minion spoofing. it is now legal to spoof the minion in prod
	for arg in sys.argv[1:]:
		if arg.startswith("minion="):  # e.g. minion=dave
			kv = arg.split("=")  #  == (minion, dave)
			newminion = kv[1] + kv[0]  #  == daveminion
			logger.warning(f"USING SPOOFED MINION '{newminion}' INSTEAD OF '{Maint.computername}'")
			Maint.computername = newminion.lower()
			break
	try:
		Maint.mioskid = minions[Maint.computername]  # e.g. '058', '060'
		_logger.set_mid(Maint.mioskid)
	except KeyError:
		logger.error("'{}' is not a registered miosk".format(Maint.computername))
		print("---------------------------------------\n"
			  "  If you wish to register this miosk,\n"
			  "there must be an entry on the database.\n"
			  "       Your temporary ID is 000\n"
			  "---------------------------------------")
		Maint.mioskid = "000"

	Maint.config_file = "kiosk{}.conf".format(Maint.mioskid)

	if not skip_maint_load:
		if not Maint.load_from_json(Maint.config_file):
			logger.warning("using default config instead")
			logger.error("You SHOULD provide a valid kiosk{}.conf!".format(Maint.mioskid))
			if not Maint.load_from_json("kiosk.conf"):
				logger.error("Failed to load backup. Please fix the main issue before running again.")

		# TODO: move this
		if not os.path.exists("employee_log.txt"):
			open("employee_log.txt", 'x')  # create

		if Maint.load_polys():
			logger.info("Successfully loaded calibration polynomials")
		else:
			logger.warning("Failed to load calibration polynomials")

	Database.table("minionSettings").set_filter(minion=Maint.mioskid)
