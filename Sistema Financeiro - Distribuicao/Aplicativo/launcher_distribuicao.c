#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void shell_quote(const char *input, char *output, size_t output_size) {
    size_t pos = 0;
    if (pos < output_size) {
        output[pos++] = '\'';
    }
    for (const char *p = input; *p && pos + 5 < output_size; p++) {
        if (*p == '\'') {
            memcpy(output + pos, "'\\''", 4);
            pos += 4;
        } else {
            output[pos++] = *p;
        }
    }
    if (pos < output_size) {
        output[pos++] = '\'';
    }
    if (pos < output_size) {
        output[pos] = '\0';
    } else if (output_size > 0) {
        output[output_size - 1] = '\0';
    }
}

int main(void) {
    const char *home = getenv("HOME");
    if (!home || home[0] == '\0') {
        return 1;
    }

    char project_dir[PATH_MAX];
    snprintf(project_dir, sizeof(project_dir), "%s/Documents/Sistema Financeiro", home);

    char quoted_project_dir[PATH_MAX + 16];
    shell_quote(project_dir, quoted_project_dir, sizeof(quoted_project_dir));

    const char *url = "http://sistema-financeiro.localhost:8010";
    char check[512];
    char start[PATH_MAX * 2];
    char open_url[512];

    snprintf(check, sizeof(check), "/usr/bin/curl -fsS --max-time 1 %s >/dev/null 2>&1", url);
    snprintf(
        start,
        sizeof(start),
        "cd %s && mkdir -p data && "
        "APP_HOST=127.0.0.1 APP_PORT=8010 APP_URL='%s' "
        "/usr/bin/nohup /usr/bin/python3 app.py >> data/server.log 2>&1 </dev/null &",
        quoted_project_dir,
        url
    );
    snprintf(open_url, sizeof(open_url), "/usr/bin/open %s >/dev/null 2>&1 &", url);

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
