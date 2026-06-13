#include <stdlib.h>
#include <unistd.h>

int main(void) {
    const char *check =
        "/usr/bin/curl -fsS --max-time 1 http://localhost:8000 >/dev/null 2>&1";
    const char *start =
        "cd '/Users/sansquer/Documents/Sistema Financeiro' && "
        "mkdir -p data && "
        "/usr/bin/python3 app.py >> data/server.log 2>&1 </dev/null &";
    const char *open_url =
        "/usr/bin/open http://localhost:8000 >/dev/null 2>&1 &";

    if (system(check) != 0) {
        system(start);
        sleep(1);
    }

    system(open_url);
    return 0;
}
