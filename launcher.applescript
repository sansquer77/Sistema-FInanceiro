set projectDir to "/Users/sansquer/Documents/Sistema Financeiro"
set appUrl to "http://localhost:8000"

on run
	set checkCommand to "/usr/bin/curl -fsS --max-time 1 " & (quoted form of appUrl) & " >/dev/null 2>&1"
	set serverCommand to "cd " & (quoted form of projectDir) & " && mkdir -p data && /usr/bin/python3 app.py >> data/server.log 2>&1 </dev/null &!"
	set browserCommand to "/usr/bin/open " & (quoted form of appUrl) & " >/dev/null 2>&1 &"

	try
		do shell script (checkCommand)
	on error
		do shell script ("/bin/zsh -lc " & (quoted form of serverCommand))
		delay 1
	end try

	do shell script (browserCommand)
	quit
end run
