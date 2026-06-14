set projectDir to "/Users/sansquer/Documents/GitHub/Sistema FInanceiro"
set appPort to "8010"
set appUrl to "http://sistema-financeiro.localhost:" & appPort

on run
	set checkCommand to "/usr/bin/curl -fsS --max-time 1 " & (quoted form of appUrl) & " >/dev/null 2>&1"
	set serverCommand to "cd " & (quoted form of projectDir) & " && mkdir -p data && APP_HOST=127.0.0.1 APP_PORT=" & appPort & " APP_URL=" & (quoted form of appUrl) & " /usr/bin/nohup /usr/bin/python3 app.py >> data/server.log 2>&1 </dev/null &!"
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
