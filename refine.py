# -*- coding: utf-8 -*-
"""调用大模型把每篇新闻精炼成一句话摘要。摘要写入 data/{date}.json 各 item 的 summary 字段。
环境变量: LLM_API_KEY / LLM_BASE_URL(默认 https://api.moonshot.cn/v1) / LLM_MODEL(默认 moonshot-v1-8k)
"""
import json, glob, os, time, datetime

def client():
    from openai import OpenAI
    return OpenAI(api_key=os.environ["LLM_API_KEY"],
                  base_url=os.environ.get("LLM_BASE_URL", "https://api.moonshot.cn/v1"))

def refine_one(c, title, text):
    if not text or len(text) < 30:
        return ""
    prompt = ("你是新闻编辑。将下面这条新闻精炼成一句不超过60字的摘要，只保留关键事实"
              "（人物、事件、数字、结论），不要评价、不要扩写。若原文是广告或无实质内容，返回空。\n\n"
              f"标题：{title}\n正文：{text[:2500]}\n\n摘要：")
    r = c.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "moonshot-v1-8k"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2, max_tokens=120)
    return r.choices[0].message.content.strip()

def main():
    path = sorted(glob.glob("data/*.json"))[-1]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    c = client()
    n_ok = n_fail = 0
    for paper in data["papers"].values():
        for it in paper["items"]:
            if it.get("summary"): continue
            try:
                it["summary"] = refine_one(c, it["title"], it.get("text", ""))
                n_ok += 1
                time.sleep(0.4)
            except Exception as e:
                print("refine fail:", it["title"][:20], e)
                it["summary"] = ""
                n_fail += 1
                time.sleep(2)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"refined {n_ok}, failed {n_fail} -> {path}")

if __name__ == "__main__":
    main()
