Search.setIndex({"docnames": ["API", "api/iqm_client", "api/iqm_client.iqm_client", "api/iqm_client.iqm_client.APITimeoutError", "api/iqm_client.iqm_client.AuthRequest", "api/iqm_client.iqm_client.Circuit", "api/iqm_client.iqm_client.CircuitExecutionError", "api/iqm_client.iqm_client.CircuitMeasurementResults", "api/iqm_client.iqm_client.ClientAuthenticationError", "api/iqm_client.iqm_client.ClientConfigurationError", "api/iqm_client.iqm_client.Credentials", "api/iqm_client.iqm_client.ExternalToken", "api/iqm_client.iqm_client.GrantType", "api/iqm_client.iqm_client.IQMClient", "api/iqm_client.iqm_client.Instruction", "api/iqm_client.iqm_client.Metadata", "api/iqm_client.iqm_client.RunRequest", "api/iqm_client.iqm_client.RunResult", "api/iqm_client.iqm_client.RunStatus", "api/iqm_client.iqm_client.SingleQubitMapping", "api/iqm_client.iqm_client.Status", "api/iqm_client.iqm_client.serialize_qubit_mapping", "authors", "changelog", "index", "license", "readme"], "filenames": ["API.rst", "api/iqm_client.rst", "api/iqm_client.iqm_client.rst", "api/iqm_client.iqm_client.APITimeoutError.rst", "api/iqm_client.iqm_client.AuthRequest.rst", "api/iqm_client.iqm_client.Circuit.rst", "api/iqm_client.iqm_client.CircuitExecutionError.rst", "api/iqm_client.iqm_client.CircuitMeasurementResults.rst", "api/iqm_client.iqm_client.ClientAuthenticationError.rst", "api/iqm_client.iqm_client.ClientConfigurationError.rst", "api/iqm_client.iqm_client.Credentials.rst", "api/iqm_client.iqm_client.ExternalToken.rst", "api/iqm_client.iqm_client.GrantType.rst", "api/iqm_client.iqm_client.IQMClient.rst", "api/iqm_client.iqm_client.Instruction.rst", "api/iqm_client.iqm_client.Metadata.rst", "api/iqm_client.iqm_client.RunRequest.rst", "api/iqm_client.iqm_client.RunResult.rst", "api/iqm_client.iqm_client.RunStatus.rst", "api/iqm_client.iqm_client.SingleQubitMapping.rst", "api/iqm_client.iqm_client.Status.rst", "api/iqm_client.iqm_client.serialize_qubit_mapping.rst", "authors.rst", "changelog.rst", "index.rst", "license.rst", "readme.rst"], "titles": ["API Reference", "iqm_client", "iqm_client.iqm_client", "iqm_client.iqm_client.APITimeoutError", "iqm_client.iqm_client.AuthRequest", "iqm_client.iqm_client.Circuit", "iqm_client.iqm_client.CircuitExecutionError", "iqm_client.iqm_client.CircuitMeasurementResults", "iqm_client.iqm_client.ClientAuthenticationError", "iqm_client.iqm_client.ClientConfigurationError", "iqm_client.iqm_client.Credentials", "iqm_client.iqm_client.ExternalToken", "iqm_client.iqm_client.GrantType", "iqm_client.iqm_client.IQMClient", "iqm_client.iqm_client.Instruction", "iqm_client.iqm_client.Metadata", "iqm_client.iqm_client.RunRequest", "iqm_client.iqm_client.RunResult", "iqm_client.iqm_client.RunStatus", "iqm_client.iqm_client.SingleQubitMapping", "iqm_client.iqm_client.Status", "iqm_client.iqm_client.serialize_qubit_mapping", "Contributors", "Changelog", "IQM client", "License", "IQM Client"], "terms": {"client": [1, 2, 4, 23], "side": [1, 24, 26], "librari": [1, 23, 24, 26], "connect": [1, 2, 24, 26], "execut": [1, 2, 3, 5, 13, 15, 16, 17, 18, 23, 25, 26], "quantum": [1, 2, 5, 13, 14, 15, 16, 23, 24, 26], "circuit": [1, 7, 13, 14, 15, 16, 17, 23], "iqm": [1, 2, 13, 16, 21, 23], "comput": [1, 2, 13, 16, 23, 24, 25, 26], "subpackag": 1, "modul": [1, 2, 24], "server": [2, 3, 4, 6, 10, 11, 13, 23], "interfac": [2, 25], "The": [2, 7, 25], "class": [2, 4, 5, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 25], "repres": [2, 21, 25], "consist": [2, 25], "list": [2, 7, 13, 15, 16, 17, 18, 21, 23, 25], "nativ": [2, 23], "oper": [2, 7, 14], "each": [2, 7, 15, 16, 25], "an": [2, 4, 11, 13, 14, 16, 17, 18, 23, 24, 25, 26], "instanc": 2, "differ": [2, 25], "type": [2, 4, 5, 12, 13, 17, 18, 21, 23, 25], "ar": [2, 10, 11, 17, 23, 25], "distinguish": 2, "name": [2, 4, 5, 13, 14, 15, 16, 19, 21, 25], "act": [2, 14, 25], "number": [2, 13], "qubit": [2, 5, 7, 13, 14, 15, 16, 19, 21, 23], "expect": [2, 23], "certain": [2, 23], "arg": [2, 14, 23], "we": [2, 25], "current": [2, 10, 11, 17, 18], "support": [2, 23, 25], "three": 2, "descript": [2, 23, 25], "1": [2, 13, 24, 25], "kei": [2, 7], "str": [2, 4, 5, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 21, 23], "z": 2, "basi": [2, 25], "phased_rx": [2, 23], "angle_t": 2, "float": [2, 13], "phase_t": 2, "x": [2, 23], "rotat": 2, "gate": 2, "2": [2, 24, 25, 26], "control": [2, 25], "result": [2, 7, 13, 17, 18, 23, 25], "take": [2, 3], "one": [2, 13, 23, 25], "string": 2, "argument": [2, 4, 5, 10, 11, 13, 14, 15, 16, 17, 18, 19, 23], "denot": 2, "label": 2, "all": [2, 4, 5, 13, 16, 25], "must": [2, 13, 16, 25], "uniqu": 2, "mai": [2, 25], "onli": [2, 4, 25], "onc": 2, "last": 2, "i": [2, 4, 13, 17, 23, 25, 26], "e": [2, 11], "cannot": [2, 4, 5, 10, 11, 14, 15, 16, 17, 18, 19, 25], "follow": [2, 25], "exampl": [2, 23, 25, 26], "alic": 2, "bob": 2, "charli": 2, "m1": 2, "conjug": 2, "two": 2, "angl": 2, "both": 2, "unit": 2, "full": 2, "turn": 2, "pi": 2, "radian": 2, "standard": 2, "matrix": 2, "r": 2, "theta": 2, "phi": 2, "exp": 2, "co": 2, "y": 2, "sin": 2, "r_z": 2, "r_x": 2, "dagger": 2, "where": [2, 25], "pauli": 2, "matric": 2, "0": [2, 24, 25, 26], "7": [2, 24, 25], "25": 2, "text": [2, 25], "diag": 2, "symmetr": 2, "wrt": 2, "": [2, 11, 15, 16, 17, 25], "ensur": 2, "after": 2, "subsystem": 2, "span": 2, "when": [2, 3, 23], "befor": [2, 13], "have": [2, 25], "been": [2, 25], "complet": 2, "runresult": [2, 13, 18, 23], "If": [2, 13, 17, 25, 26], "run": [2, 13, 17, 18, 23], "succeed": 2, "contain": [2, 25], "batch": [2, 13, 15, 16, 17, 23], "It": [2, 4], "dictionari": 2, "dict": [2, 13, 14, 16, 17, 18, 21, 23], "map": [2, 7, 13, 15, 16, 17, 18, 19, 21], "2d": 2, "arrai": 2, "nest": 2, "circuit_index": 2, "shot": [2, 7, 13, 15, 16], "qubit_index": 2, "th": 2, "non": [2, 25], "neg": 2, "integ": 2, "state": [2, 25], "wa": [2, 13, 25], "outcom": 2, "attribut": [2, 4, 5, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 25], "function": [2, 23], "except": [2, 3, 6, 8, 9, 13, 23, 25], "inherit": 2, "clientconfigurationerror": 2, "clientauthenticationerror": [2, 13], "circuitexecutionerror": [2, 13], "apitimeouterror": [2, 13], "statu": [2, 13, 17, 18, 23], "enum": [2, 12, 20], "pydant": [2, 23], "main": 2, "basemodel": [2, 4, 5, 10, 11, 14, 15, 16, 17, 18, 19], "util": 2, "represent": 2, "singlequbitmap": [2, 15, 16, 21], "runrequest": [2, 23], "metadata": [2, 17, 23], "runstatu": [2, 13], "granttyp": [2, 4], "authrequest": 2, "credenti": [2, 13], "externaltoken": 2, "iqmclient": [2, 23], "task": [3, 13, 20], "too": 3, "long": [3, 13], "client_id": 4, "grant_typ": 4, "none": [4, 10, 11, 13, 15, 16, 17, 18], "usernam": [4, 10, 13, 23], "password": [4, 10, 13, 23], "refresh_token": [4, 10], "base": [4, 5, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 25], "request": [4, 12, 13, 16, 17, 18, 23], "sent": [4, 13, 23, 25], "authent": [4, 8, 10, 11, 13, 23], "access": [4, 10, 11, 13, 23], "token": [4, 10, 11, 12, 13, 23], "refresh": [4, 10], "termin": [4, 13, 25], "session": [4, 10, 11, 13, 23], "grant": [4, 25], "start": [4, 13], "new": [4, 5, 10, 11, 14, 15, 16, 17, 18, 19, 23], "us": [4, 13, 15, 16, 23, 25, 26], "field": [4, 10, 11, 13, 16, 23, 25], "maintain": [4, 10, 11], "exist": 4, "logout": [4, 13], "creat": [4, 5, 10, 11, 13, 14, 15, 16, 17, 18, 19], "model": [4, 5, 10, 11, 14, 15, 16, 17, 18, 19], "pars": [4, 5, 10, 11, 14, 15, 16, 17, 18, 19, 23], "valid": [4, 5, 10, 11, 14, 15, 16, 17, 18, 19, 23], "input": [4, 5, 10, 11, 14, 15, 16, 17, 18, 19], "data": [4, 5, 10, 11, 13, 14, 15, 16, 17, 18, 19, 21], "from": [4, 5, 7, 10, 11, 14, 15, 16, 17, 18, 19, 21, 23, 25, 26], "keyword": [4, 5, 10, 11, 13, 14, 15, 16, 17, 18, 19], "rais": [4, 5, 10, 11, 13, 14, 15, 16, 17, 18, 19, 23], "validationerror": [4, 5, 10, 11, 14, 15, 16, 17, 18, 19], "form": [4, 5, 10, 11, 14, 15, 16, 17, 18, 19, 25], "method": [4, 5, 7, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20], "paramet": [4, 5, 10, 11, 13, 14, 15, 16, 17, 18, 19, 21, 23], "instruct": [5, 23], "tupl": [5, 14, 23], "compris": 5, "all_qubit": 5, "return": [5, 13, 17, 18, 21], "set": [5, 13, 15, 16, 23], "someth": [6, 8], "went": [6, 8], "wrong": [6, 8, 9], "measur": [7, 16, 17, 23], "singl": 7, "For": [7, 25, 26], "correspond": [7, 21], "outer": 7, "element": 7, "inner": 7, "user": [8, 10, 23, 26], "configur": [9, 23, 25], "provid": [9, 10, 13, 25], "auth_server_url": [10, 11, 13], "access_token": [10, 11], "load": [10, 11], "period": 10, "url": [10, 11, 13, 23], "log": [10, 13], "extern": [11, 13, 23], "manag": [11, 13, 23, 25], "resourc": 11, "g": 11, "file": [11, 13, 23, 25], "gener": [11, 25], "cortex": 11, "cli": 11, "valu": [12, 17, 18, 20], "tokens_fil": 13, "object": [13, 21, 25], "endpoint": [13, 23], "ha": [13, 17, 18, 25], "http": [13, 23, 25], "option": [13, 23], "path": 13, "thi": [13, 16, 25, 26], "can": [13, 23, 26], "also": [13, 25], "iqm_tokens_fil": 13, "environ": 13, "variabl": 13, "iqm_auth_serv": 13, "unset": 13, "unauthent": 13, "iqm_auth_usernam": 13, "iqm_auth_password": 13, "submit_circuit": [13, 23], "qubit_map": [13, 15, 16, 21, 23], "custom_set": [13, 16, 23], "calibration_set_id": [13, 15, 16, 23], "submit": [13, 23, 25], "human": [13, 26], "readabl": [13, 25], "logic": [13, 14, 15, 16, 19, 21], "physic": [13, 15, 16, 19, 21], "alreadi": 13, "note": [13, 16], "ani": [13, 14, 16, 25], "custom": [13, 16], "overwrit": [13, 16], "default": [13, 16, 23], "calibr": [13, 15, 16, 23], "should": [13, 16, 25], "alwai": [13, 16], "normal": [13, 16, 25], "int": [13, 15, 16, 17], "id": [13, 15, 16, 23], "instead": [13, 23], "time": [13, 15, 16], "need": 13, "queri": 13, "uuid": 13, "get_run": 13, "job_id": 13, "pend": [13, 17, 18], "httpexcept": 13, "specif": [13, 25], "get_run_statu": [13, 23], "wait_for_result": 13, "timeout_sec": 13, "900": 13, "poll": [13, 23], "until": 13, "readi": [13, 17, 18], "fail": [13, 16, 17, 18], "out": [13, 25], "wait": [13, 23], "how": [13, 15, 16, 25], "respons": [13, 23, 25], "exceed": 13, "timeout": [13, 23], "close_auth_sess": [13, 23], "true": 13, "iff": [13, 17], "successfulli": [13, 17], "close": [13, 23], "ask": [13, 23], "bool": 13, "belong": 15, "job": [15, 17, 23], "sumiss": 15, "mani": [15, 16], "were": 15, "specifi": 15, "same": [16, 25], "otherwis": [16, 25], "hardwar": 16, "latest": 16, "messag": [17, 18], "warn": [17, 18, 23], "present": 17, "carri": [17, 25], "addit": [17, 25], "inform": [17, 25], "finish": 17, "error": [17, 18, 23], "about": 17, "underli": 17, "static": [17, 18], "from_dict": [17, 18], "inp": [17, 18], "union": [17, 18, 25], "batchcircuit": 18, "logical_nam": 19, "physical_nam": 19, "serial": 21, "transfer": [21, 25], "format": [21, 25], "olli": 22, "ahonen": 22, "meetiqm": 22, "com": 22, "vill": 22, "bergholm": 22, "maija": 22, "nevala": 22, "hayk": 22, "sargsyan": 22, "maxim": 22, "smirnov": 22, "dc914337": 22, "gmail": 22, "tyrkk\u00f6": 22, "otyrkko": 22, "rakhim": 22, "davletkaliyev": 22, "chang": [23, 25], "49": 23, "remov": 23, "add": [23, 25], "48": 23, "increas": 23, "interv": 23, "while": [23, 25], "47": 23, "document": [23, 25], "45": 23, "43": 23, "42": 23, "enabl": 23, "mypi": 23, "check": 23, "41": 23, "updat": 23, "sourc": [23, 24, 25], "code": [23, 24, 25, 26], "accord": 23, "pylint": 23, "v2": 23, "15": 23, "40": 23, "renam": 23, "39": 23, "try": 23, "automat": 23, "delet": 23, "show": 23, "coco": 23, "401": 23, "move": 23, "constructor": 23, "31": 23, "now": 23, "import": [23, 25], "iqm_client": [23, 24], "37": 23, "includ": [23, 25], "develop": [23, 26], "releas": [23, 24, 26], "subdirectori": 23, "36": 23, "without": [23, 25], "35": 23, "implement": 23, "34": 23, "make": [23, 25], "30": [23, 24], "get": 23, "29": 23, "mention": 23, "barrier": 23, "28": 23, "retriev": 23, "26": 23, "requir": [23, 25], "publish": 23, "json": 23, "schema": 23, "24": 23, "python": [23, 26], "23": 23, "22": 23, "21": 23, "20": 23, "100": 23, "continu": 23, "header": 23, "post": 23, "18": 23, "bump": 23, "depend": 23, "13": 23, "minor": 23, "doc": 23, "emit": 23, "userwarn": 23, "tag": 23, "basic": 23, "auth": 23, "unneed": 23, "split": 23, "cirq": [23, 26], "8": [24, 25], "date": [24, 25], "2022": [24, 26], "09": 24, "finland": 24, "instal": 24, "copyright": [24, 25], "api": 24, "refer": 24, "licens": [24, 26], "contributor": [24, 25], "changelog": 24, "version": [24, 25, 26], "3": [24, 25], "6": [24, 25], "5": [24, 25], "4": [24, 25], "10": 24, "9": [24, 25], "index": [24, 26], "search": 24, "page": [24, 25], "apach": [25, 26], "januari": 25, "2004": 25, "www": 25, "org": 25, "term": 25, "AND": 25, "condit": 25, "FOR": 25, "reproduct": 25, "distribut": 25, "definit": 25, "shall": 25, "mean": 25, "defin": 25, "section": 25, "through": 25, "licensor": 25, "owner": 25, "entiti": 25, "author": 25, "legal": 25, "other": 25, "under": [25, 26], "common": 25, "purpos": 25, "power": 25, "direct": 25, "indirect": 25, "caus": 25, "whether": 25, "contract": 25, "ii": 25, "ownership": 25, "fifti": 25, "percent": 25, "50": 25, "more": 25, "outstand": 25, "share": 25, "iii": 25, "benefici": 25, "you": [25, 26], "your": 25, "individu": 25, "exercis": 25, "permiss": 25, "prefer": 25, "modif": 25, "limit": 25, "softwar": [25, 26], "mechan": 25, "transform": 25, "translat": 25, "compil": 25, "convers": 25, "media": 25, "work": 25, "authorship": 25, "made": 25, "avail": 25, "indic": 25, "notic": 25, "attach": 25, "appendix": 25, "below": 25, "deriv": 25, "which": 25, "editori": 25, "revis": 25, "annot": 25, "elabor": 25, "whole": 25, "origin": 25, "remain": 25, "separ": 25, "mere": 25, "link": 25, "bind": 25, "thereof": 25, "contribut": 25, "intention": 25, "inclus": 25, "behalf": 25, "electron": 25, "verbal": 25, "written": 25, "commun": 25, "its": 25, "mail": 25, "system": 25, "issu": 25, "track": 25, "discuss": 25, "improv": 25, "exclud": 25, "conspicu": 25, "mark": 25, "design": 25, "write": 25, "Not": 25, "whom": 25, "receiv": 25, "subsequ": 25, "incorpor": 25, "within": 25, "subject": 25, "herebi": 25, "perpetu": 25, "worldwid": 25, "exclus": 25, "charg": 25, "royalti": 25, "free": [25, 26], "irrevoc": 25, "reproduc": 25, "prepar": 25, "publicli": 25, "displai": 25, "perform": 25, "sublicens": 25, "patent": 25, "offer": 25, "sell": 25, "appli": 25, "those": 25, "claim": 25, "necessarili": 25, "infring": 25, "alon": 25, "combin": 25, "institut": 25, "litig": 25, "against": 25, "cross": 25, "counterclaim": 25, "lawsuit": 25, "alleg": 25, "constitut": 25, "contributori": 25, "redistribut": 25, "copi": 25, "medium": 25, "meet": 25, "give": 25, "recipi": 25, "b": 25, "modifi": 25, "promin": 25, "c": 25, "retain": 25, "trademark": 25, "do": 25, "pertain": 25, "part": 25, "d": 25, "least": 25, "place": 25, "along": 25, "wherev": 25, "third": 25, "parti": 25, "appear": 25, "content": 25, "own": 25, "alongsid": 25, "addendum": 25, "constru": 25, "statement": 25, "compli": 25, "submiss": 25, "unless": 25, "explicitli": 25, "notwithstand": 25, "abov": 25, "noth": 25, "herein": 25, "supersed": 25, "agreement": 25, "regard": 25, "doe": 25, "trade": 25, "servic": 25, "product": 25, "reason": 25, "customari": 25, "describ": 25, "disclaim": 25, "warranti": 25, "applic": 25, "law": 25, "agre": 25, "AS": 25, "OR": 25, "OF": 25, "kind": 25, "either": 25, "express": 25, "impli": 25, "titl": 25, "merchant": 25, "fit": 25, "A": 25, "particular": 25, "sole": 25, "determin": 25, "appropri": 25, "assum": 25, "risk": 25, "associ": 25, "liabil": 25, "In": 25, "event": 25, "theori": 25, "tort": 25, "neglig": 25, "deliber": 25, "grossli": 25, "liabl": 25, "damag": 25, "special": 25, "incident": 25, "consequenti": 25, "charact": 25, "aris": 25, "inabl": 25, "loss": 25, "goodwil": 25, "stoppag": 25, "failur": 25, "malfunct": 25, "commerci": 25, "even": 25, "advis": 25, "possibl": 25, "accept": 25, "choos": 25, "fee": 25, "indemn": 25, "oblig": 25, "right": 25, "howev": 25, "indemnifi": 25, "defend": 25, "hold": 25, "harmless": 25, "incur": 25, "assert": 25, "end": 25, "To": 25, "boilerpl": 25, "enclos": 25, "bracket": 25, "replac": 25, "identifi": 25, "don": 25, "t": 25, "comment": 25, "syntax": 25, "recommend": 25, "print": 25, "easier": 25, "identif": 25, "archiv": 25, "yyyi": 25, "complianc": 25, "obtain": 25, "see": 25, "languag": 25, "govern": 25, "intend": 26, "directli": 26, "want": 26, "just": 26, "though": 26, "packag": 26, "pypi": 26, "pip": 26, "2021": 26}, "objects": {"": [[1, 0, 0, "-", "iqm_client"]], "iqm_client": [[2, 0, 0, "-", "iqm_client"]], "iqm_client.iqm_client": [[3, 1, 1, "", "APITimeoutError"], [4, 2, 1, "", "AuthRequest"], [5, 2, 1, "", "Circuit"], [6, 1, 1, "", "CircuitExecutionError"], [7, 3, 1, "", "CircuitMeasurementResults"], [8, 1, 1, "", "ClientAuthenticationError"], [9, 1, 1, "", "ClientConfigurationError"], [10, 2, 1, "", "Credentials"], [11, 2, 1, "", "ExternalToken"], [12, 2, 1, "", "GrantType"], [13, 2, 1, "", "IQMClient"], [14, 2, 1, "", "Instruction"], [15, 2, 1, "", "Metadata"], [16, 2, 1, "", "RunRequest"], [17, 2, 1, "", "RunResult"], [18, 2, 1, "", "RunStatus"], [19, 2, 1, "", "SingleQubitMapping"], [20, 2, 1, "", "Status"], [21, 5, 1, "", "serialize_qubit_mapping"]], "iqm_client.iqm_client.AuthRequest": [[4, 3, 1, "", "client_id"], [4, 3, 1, "", "grant_type"], [4, 3, 1, "", "password"], [4, 3, 1, "", "refresh_token"], [4, 3, 1, "", "username"]], "iqm_client.iqm_client.Circuit": [[5, 4, 1, "", "all_qubits"], [5, 3, 1, "", "instructions"], [5, 3, 1, "", "name"]], "iqm_client.iqm_client.Credentials": [[10, 3, 1, "", "access_token"], [10, 3, 1, "", "auth_server_url"], [10, 3, 1, "", "password"], [10, 3, 1, "", "refresh_token"], [10, 3, 1, "", "username"]], "iqm_client.iqm_client.ExternalToken": [[11, 3, 1, "", "access_token"], [11, 3, 1, "", "auth_server_url"]], "iqm_client.iqm_client.IQMClient": [[13, 4, 1, "", "close_auth_session"], [13, 4, 1, "", "get_run"], [13, 4, 1, "", "get_run_status"], [13, 4, 1, "", "submit_circuits"], [13, 4, 1, "", "wait_for_results"]], "iqm_client.iqm_client.Instruction": [[14, 3, 1, "", "args"], [14, 3, 1, "", "name"], [14, 3, 1, "", "qubits"]], "iqm_client.iqm_client.Metadata": [[15, 3, 1, "", "calibration_set_id"], [15, 3, 1, "", "circuits"], [15, 3, 1, "", "qubit_mapping"], [15, 3, 1, "", "shots"]], "iqm_client.iqm_client.RunRequest": [[16, 3, 1, "", "calibration_set_id"], [16, 3, 1, "", "circuits"], [16, 3, 1, "", "custom_settings"], [16, 3, 1, "", "qubit_mapping"], [16, 3, 1, "", "shots"]], "iqm_client.iqm_client.RunResult": [[17, 4, 1, "", "from_dict"], [17, 3, 1, "", "measurements"], [17, 3, 1, "", "message"], [17, 3, 1, "", "metadata"], [17, 3, 1, "", "status"], [17, 3, 1, "", "warnings"]], "iqm_client.iqm_client.RunStatus": [[18, 4, 1, "", "from_dict"], [18, 3, 1, "", "message"], [18, 3, 1, "", "status"], [18, 3, 1, "", "warnings"]], "iqm_client.iqm_client.SingleQubitMapping": [[19, 3, 1, "", "logical_name"], [19, 3, 1, "", "physical_name"]]}, "objtypes": {"0": "py:module", "1": "py:exception", "2": "py:class", "3": "py:attribute", "4": "py:method", "5": "py:function"}, "objnames": {"0": ["py", "module", "Python module"], "1": ["py", "exception", "Python exception"], "2": ["py", "class", "Python class"], "3": ["py", "attribute", "Python attribute"], "4": ["py", "method", "Python method"], "5": ["py", "function", "Python function"]}, "titleterms": {"api": 0, "refer": 0, "iqm_client": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21], "instruct": [2, 14], "measur": 2, "phase": 2, "rx": 2, "cz": 2, "barrier": 2, "circuit": [2, 5], "output": 2, "apitimeouterror": 3, "authrequest": 4, "circuitexecutionerror": 6, "circuitmeasurementresult": 7, "clientauthenticationerror": 8, "clientconfigurationerror": 9, "credenti": 10, "externaltoken": 11, "granttyp": 12, "iqmclient": 13, "metadata": 15, "runrequest": 16, "runresult": 17, "runstatu": 18, "singlequbitmap": 19, "statu": 20, "serialize_qubit_map": 21, "contributor": 22, "changelog": 23, "version": 23, "8": 23, "1": 23, "0": 23, "7": 23, "3": 23, "2": 23, "6": 23, "5": 23, "4": 23, "10": 23, "9": 23, "featur": 23, "fix": 23, "iqm": [24, 26], "client": [24, 26], "content": 24, "indic": 24, "tabl": 24, "licens": 25, "instal": 26, "copyright": 26}, "envversion": {"sphinx.domains.c": 2, "sphinx.domains.changeset": 1, "sphinx.domains.citation": 1, "sphinx.domains.cpp": 8, "sphinx.domains.index": 1, "sphinx.domains.javascript": 2, "sphinx.domains.math": 2, "sphinx.domains.python": 3, "sphinx.domains.rst": 2, "sphinx.domains.std": 2, "sphinx.ext.todo": 2, "sphinx.ext.intersphinx": 1, "sphinx": 57}, "alltitles": {"API Reference": [[0, "api-reference"]], "iqm_client": [[1, "module-iqm_client"]], "iqm_client.iqm_client": [[2, "module-iqm_client.iqm_client"]], "Instructions": [[2, "instructions"]], "Measurement": [[2, "measurement"]], "Phased Rx": [[2, "phased-rx"]], "CZ": [[2, "cz"]], "Barrier": [[2, "barrier"]], "Circuit output": [[2, "circuit-output"]], "iqm_client.iqm_client.APITimeoutError": [[3, "iqm-client-iqm-client-apitimeouterror"]], "iqm_client.iqm_client.AuthRequest": [[4, "iqm-client-iqm-client-authrequest"]], "iqm_client.iqm_client.Circuit": [[5, "iqm-client-iqm-client-circuit"]], "iqm_client.iqm_client.CircuitExecutionError": [[6, "iqm-client-iqm-client-circuitexecutionerror"]], "iqm_client.iqm_client.CircuitMeasurementResults": [[7, "iqm-client-iqm-client-circuitmeasurementresults"]], "iqm_client.iqm_client.ClientAuthenticationError": [[8, "iqm-client-iqm-client-clientauthenticationerror"]], "iqm_client.iqm_client.ClientConfigurationError": [[9, "iqm-client-iqm-client-clientconfigurationerror"]], "iqm_client.iqm_client.Credentials": [[10, "iqm-client-iqm-client-credentials"]], "iqm_client.iqm_client.ExternalToken": [[11, "iqm-client-iqm-client-externaltoken"]], "iqm_client.iqm_client.GrantType": [[12, "iqm-client-iqm-client-granttype"]], "iqm_client.iqm_client.IQMClient": [[13, "iqm-client-iqm-client-iqmclient"]], "iqm_client.iqm_client.Instruction": [[14, "iqm-client-iqm-client-instruction"]], "iqm_client.iqm_client.Metadata": [[15, "iqm-client-iqm-client-metadata"]], "iqm_client.iqm_client.RunRequest": [[16, "iqm-client-iqm-client-runrequest"]], "iqm_client.iqm_client.RunResult": [[17, "iqm-client-iqm-client-runresult"]], "iqm_client.iqm_client.RunStatus": [[18, "iqm-client-iqm-client-runstatus"]], "iqm_client.iqm_client.SingleQubitMapping": [[19, "iqm-client-iqm-client-singlequbitmapping"]], "iqm_client.iqm_client.Status": [[20, "iqm-client-iqm-client-status"]], "iqm_client.iqm_client.serialize_qubit_mapping": [[21, "iqm-client-iqm-client-serialize-qubit-mapping"]], "Contributors": [[22, "contributors"]], "Changelog": [[23, "changelog"]], "Version 8.1": [[23, "version-8-1"]], "Version 8.0": [[23, "version-8-0"]], "Version 7.3": [[23, "version-7-3"]], "Version 7.2": [[23, "version-7-2"]], "Version 7.1": [[23, "version-7-1"]], "Version 7.0": [[23, "version-7-0"]], "Version 6.2": [[23, "version-6-2"]], "Version 6.1": [[23, "version-6-1"]], "Version 6.0": [[23, "version-6-0"]], "Version 5.0": [[23, "version-5-0"]], "Version 4.3": [[23, "version-4-3"]], "Version 4.2": [[23, "version-4-2"]], "Version 4.1": [[23, "version-4-1"]], "Version 4.0": [[23, "version-4-0"]], "Version 3.3": [[23, "version-3-3"]], "Version 3.2": [[23, "version-3-2"]], "Version 3.1": [[23, "version-3-1"]], "Version 3.0": [[23, "version-3-0"]], "Version 2.2": [[23, "version-2-2"]], "Version 2.1": [[23, "version-2-1"]], "Version 2.0": [[23, "version-2-0"]], "Version 1.10": [[23, "version-1-10"]], "Version 1.9": [[23, "version-1-9"]], "Version 1.8": [[23, "version-1-8"]], "Version 1.7": [[23, "version-1-7"]], "Version 1.6": [[23, "version-1-6"]], "Version 1.5": [[23, "version-1-5"]], "Version 1.4": [[23, "version-1-4"]], "Version 1.3": [[23, "version-1-3"]], "Features": [[23, "features"], [23, "id41"]], "Version 1.2": [[23, "version-1-2"]], "Fixes": [[23, "fixes"], [23, "id39"]], "Version 1.1": [[23, "version-1-1"]], "Version 1.0": [[23, "version-1-0"]], "IQM client": [[24, "iqm-client"]], "Contents": [[24, "contents"]], "Indices and tables": [[24, "indices-and-tables"]], "License": [[25, "license"]], "IQM Client": [[26, "iqm-client"]], "Installation": [[26, "installation"]], "Copyright": [[26, "copyright"]]}, "indexentries": {"iqm_client": [[1, "module-iqm_client"]], "module": [[1, "module-iqm_client"], [2, "module-iqm_client.iqm_client"]], "iqm_client.iqm_client": [[2, "module-iqm_client.iqm_client"]], "apitimeouterror": [[3, "iqm_client.iqm_client.APITimeoutError"]], "authrequest (class in iqm_client.iqm_client)": [[4, "iqm_client.iqm_client.AuthRequest"]], "client_id (iqm_client.iqm_client.authrequest attribute)": [[4, "iqm_client.iqm_client.AuthRequest.client_id"]], "grant_type (iqm_client.iqm_client.authrequest attribute)": [[4, "iqm_client.iqm_client.AuthRequest.grant_type"]], "password (iqm_client.iqm_client.authrequest attribute)": [[4, "iqm_client.iqm_client.AuthRequest.password"]], "refresh_token (iqm_client.iqm_client.authrequest attribute)": [[4, "iqm_client.iqm_client.AuthRequest.refresh_token"]], "username (iqm_client.iqm_client.authrequest attribute)": [[4, "iqm_client.iqm_client.AuthRequest.username"]], "circuit (class in iqm_client.iqm_client)": [[5, "iqm_client.iqm_client.Circuit"]], "all_qubits() (iqm_client.iqm_client.circuit method)": [[5, "iqm_client.iqm_client.Circuit.all_qubits"]], "instructions (iqm_client.iqm_client.circuit attribute)": [[5, "iqm_client.iqm_client.Circuit.instructions"]], "name (iqm_client.iqm_client.circuit attribute)": [[5, "iqm_client.iqm_client.Circuit.name"]], "circuitexecutionerror": [[6, "iqm_client.iqm_client.CircuitExecutionError"]], "circuitmeasurementresults (in module iqm_client.iqm_client)": [[7, "iqm_client.iqm_client.CircuitMeasurementResults"]], "clientauthenticationerror": [[8, "iqm_client.iqm_client.ClientAuthenticationError"]], "clientconfigurationerror": [[9, "iqm_client.iqm_client.ClientConfigurationError"]], "credentials (class in iqm_client.iqm_client)": [[10, "iqm_client.iqm_client.Credentials"]], "access_token (iqm_client.iqm_client.credentials attribute)": [[10, "iqm_client.iqm_client.Credentials.access_token"]], "auth_server_url (iqm_client.iqm_client.credentials attribute)": [[10, "iqm_client.iqm_client.Credentials.auth_server_url"]], "password (iqm_client.iqm_client.credentials attribute)": [[10, "iqm_client.iqm_client.Credentials.password"]], "refresh_token (iqm_client.iqm_client.credentials attribute)": [[10, "iqm_client.iqm_client.Credentials.refresh_token"]], "username (iqm_client.iqm_client.credentials attribute)": [[10, "iqm_client.iqm_client.Credentials.username"]], "externaltoken (class in iqm_client.iqm_client)": [[11, "iqm_client.iqm_client.ExternalToken"]], "access_token (iqm_client.iqm_client.externaltoken attribute)": [[11, "iqm_client.iqm_client.ExternalToken.access_token"]], "auth_server_url (iqm_client.iqm_client.externaltoken attribute)": [[11, "iqm_client.iqm_client.ExternalToken.auth_server_url"]], "granttype (class in iqm_client.iqm_client)": [[12, "iqm_client.iqm_client.GrantType"]], "iqmclient (class in iqm_client.iqm_client)": [[13, "iqm_client.iqm_client.IQMClient"]], "close_auth_session() (iqm_client.iqm_client.iqmclient method)": [[13, "iqm_client.iqm_client.IQMClient.close_auth_session"]], "get_run() (iqm_client.iqm_client.iqmclient method)": [[13, "iqm_client.iqm_client.IQMClient.get_run"]], "get_run_status() (iqm_client.iqm_client.iqmclient method)": [[13, "iqm_client.iqm_client.IQMClient.get_run_status"]], "submit_circuits() (iqm_client.iqm_client.iqmclient method)": [[13, "iqm_client.iqm_client.IQMClient.submit_circuits"]], "wait_for_results() (iqm_client.iqm_client.iqmclient method)": [[13, "iqm_client.iqm_client.IQMClient.wait_for_results"]], "instruction (class in iqm_client.iqm_client)": [[14, "iqm_client.iqm_client.Instruction"]], "args (iqm_client.iqm_client.instruction attribute)": [[14, "iqm_client.iqm_client.Instruction.args"]], "name (iqm_client.iqm_client.instruction attribute)": [[14, "iqm_client.iqm_client.Instruction.name"]], "qubits (iqm_client.iqm_client.instruction attribute)": [[14, "iqm_client.iqm_client.Instruction.qubits"]], "metadata (class in iqm_client.iqm_client)": [[15, "iqm_client.iqm_client.Metadata"]], "calibration_set_id (iqm_client.iqm_client.metadata attribute)": [[15, "iqm_client.iqm_client.Metadata.calibration_set_id"]], "circuits (iqm_client.iqm_client.metadata attribute)": [[15, "iqm_client.iqm_client.Metadata.circuits"]], "qubit_mapping (iqm_client.iqm_client.metadata attribute)": [[15, "iqm_client.iqm_client.Metadata.qubit_mapping"]], "shots (iqm_client.iqm_client.metadata attribute)": [[15, "iqm_client.iqm_client.Metadata.shots"]], "runrequest (class in iqm_client.iqm_client)": [[16, "iqm_client.iqm_client.RunRequest"]], "calibration_set_id (iqm_client.iqm_client.runrequest attribute)": [[16, "iqm_client.iqm_client.RunRequest.calibration_set_id"]], "circuits (iqm_client.iqm_client.runrequest attribute)": [[16, "iqm_client.iqm_client.RunRequest.circuits"]], "custom_settings (iqm_client.iqm_client.runrequest attribute)": [[16, "iqm_client.iqm_client.RunRequest.custom_settings"]], "qubit_mapping (iqm_client.iqm_client.runrequest attribute)": [[16, "iqm_client.iqm_client.RunRequest.qubit_mapping"]], "shots (iqm_client.iqm_client.runrequest attribute)": [[16, "iqm_client.iqm_client.RunRequest.shots"]], "runresult (class in iqm_client.iqm_client)": [[17, "iqm_client.iqm_client.RunResult"]], "from_dict() (iqm_client.iqm_client.runresult static method)": [[17, "iqm_client.iqm_client.RunResult.from_dict"]], "measurements (iqm_client.iqm_client.runresult attribute)": [[17, "iqm_client.iqm_client.RunResult.measurements"]], "message (iqm_client.iqm_client.runresult attribute)": [[17, "iqm_client.iqm_client.RunResult.message"]], "metadata (iqm_client.iqm_client.runresult attribute)": [[17, "iqm_client.iqm_client.RunResult.metadata"]], "status (iqm_client.iqm_client.runresult attribute)": [[17, "iqm_client.iqm_client.RunResult.status"]], "warnings (iqm_client.iqm_client.runresult attribute)": [[17, "iqm_client.iqm_client.RunResult.warnings"]], "runstatus (class in iqm_client.iqm_client)": [[18, "iqm_client.iqm_client.RunStatus"]], "from_dict() (iqm_client.iqm_client.runstatus static method)": [[18, "iqm_client.iqm_client.RunStatus.from_dict"]], "message (iqm_client.iqm_client.runstatus attribute)": [[18, "iqm_client.iqm_client.RunStatus.message"]], "status (iqm_client.iqm_client.runstatus attribute)": [[18, "iqm_client.iqm_client.RunStatus.status"]], "warnings (iqm_client.iqm_client.runstatus attribute)": [[18, "iqm_client.iqm_client.RunStatus.warnings"]], "singlequbitmapping (class in iqm_client.iqm_client)": [[19, "iqm_client.iqm_client.SingleQubitMapping"]], "logical_name (iqm_client.iqm_client.singlequbitmapping attribute)": [[19, "iqm_client.iqm_client.SingleQubitMapping.logical_name"]], "physical_name (iqm_client.iqm_client.singlequbitmapping attribute)": [[19, "iqm_client.iqm_client.SingleQubitMapping.physical_name"]], "status (class in iqm_client.iqm_client)": [[20, "iqm_client.iqm_client.Status"]], "serialize_qubit_mapping() (in module iqm_client.iqm_client)": [[21, "iqm_client.iqm_client.serialize_qubit_mapping"]]}})