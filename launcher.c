#include <stdlib.h>
#include <unistd.h>

int main(void) {
    const char *check =
        "/usr/bin/curl -fsS --max-time 1 http://sistema-financeiro.localhost:8010 >/dev/null 2>&1";
    const char *start =
        "cd '/Users/sansquer/Documents/Sistema Financeiro' && "
        "mkdir -p data && "
        "APP_HOST=127.0.0.1 APP_PORT=8010 APP_URL='http://sistema-financeiro.localhost:8010' "
        "/usr/bin/nohup /usr/bin/python3 app.py >> data/server.log 2>&1 </dev/null &";
    const char *open_url =
        "/usr/bin/open http://sistema-financeiro.localhost:8010 >/dev/null 2>&1 &";

    if (system(check) != 0) {
        system(start);
        for (int i = 0; i < 40; i++) {
            if (system(check) == 0) {
                break;
            }
            usleep(250000);
        }
    }

    system(open_url);
    return 0;
}
