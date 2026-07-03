set projectDir to "/Users/sansquer/Documents/GitHub/Sistema FInanceiro"
set appPort to "8010"
set appUrl to "http://sistema-financeiro.localhost:" & appPort
set exposeLan to "0"

-- Allow override via environment variable EXPOSE_LAN
try
	set envExpose to do shell script "printf '%s' \"$EXPOSE_LAN\""
	if envExpose is not "" then set exposeLan to envExpose
end try

-- If exposing, compute local IP and adjust URL
if exposeLan is "1" or exposeLan is "true" then
	try
		set localIp to do shell script "ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || python3 -c \"import socket; s=socket.socket(); s.connect(('8.8.8.8',80)); print(s.getsockname()[0])\" 2>/dev/null || echo ''"
		if localIp is not "" then
			set appUrl to "http://" & localIp & ":" & appPort
		end if
	end try
end if

on run
	set checkCommand to "/usr/bin/curl -fsS --max-time 1 " & (quoted form of appUrl) & " >/dev/null 2>&1"
	set serverCommand to "cd " & (quoted form of projectDir) & " && mkdir -p data && " & ¬
		"APP_HOST=127.0.0.1 APP_PORT=" & appPort & " APP_URL=" & (quoted form of appUrl)
	try
		set envAllowedHosts to do shell script "printf '%s' \"$APP_ALLOWED_HOSTS\""
		set envAllowedOrigins to do shell script "printf '%s' \"$APP_ALLOWED_ORIGINS\""
		if envAllowedHosts is not "" then
			set serverCommand to serverCommand & " APP_ALLOWED_HOSTS='" & envAllowedHosts & "'"
		end if
		if envAllowedOrigins is not "" then
			set serverCommand to serverCommand & " APP_ALLOWED_ORIGINS='" & envAllowedOrigins & "'"
		end if
	end try
	set serverCommand to serverCommand & " /usr/bin/nohup /usr/bin/python3 app.py >> data/server.log 2>&1 </dev/null &!"
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
