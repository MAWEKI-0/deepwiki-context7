import urllib.parse

password = "9jsh(/jsz=kaß2J"
encoded_password = urllib.parse.quote_plus(password)
print(encoded_password)
