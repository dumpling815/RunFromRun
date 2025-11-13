from common.settings import AVAILABLE,THRESHOLDS,OLLAMASETTINGS,API_KEYS,API_URLS,CAMELOT_MODE,LLM_OPTION

if __name__ == "__main__":
    #[DEBUG] for checking loaded settings
    print("AVAILABLE:", AVAILABLE)
    print(type(AVAILABLE))
    print("THRESHOLDS:", THRESHOLDS)
    print(type(THRESHOLDS))
    print("OLLAMA:", OLLAMASETTINGS)
    print(type(OLLAMASETTINGS))
    print("API_KEYS:", API_KEYS)
    print(type(API_KEYS))
    print("API_URLS:", API_URLS)
    print(type(API_URLS))
    print("CAMELOT_MODE:", CAMELOT_MODE)
    print(type(CAMELOT_MODE))
    print("LLM_OPTION:", LLM_OPTION)
    print(type(LLM_OPTION))