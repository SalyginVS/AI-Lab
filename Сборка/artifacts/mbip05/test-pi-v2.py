import importlib.util,json,copy,unittest
from pathlib import Path
p=Path(__file__).with_name("configure-pi-v2.py")
spec=importlib.util.spec_from_file_location("v2",p);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class Test(unittest.TestCase):
 def setUp(self):
    self.m={"providers":{"ailab-ollama":{"models":[{"id":"old"}]},"ailab-strata":{"baseUrl":"http://127.0.0.1:18081/v1","api":"openai-completions","models":[{"id":v.PILOT,"reasoning":True}]}}}
    self.s={"defaultProvider":"ailab-ollama","defaultModel":"old","defaultThinkingLevel":"max","compaction":{"reserveTokens":32768,"keepRecentTokens":20000,"modelOverrides":{"ailab-ollama/old":{"reserveTokens":32768}}},"retry":{"enabled":False}}
 def test_preserve(self):
    m,s=v.evolve(self.m,self.s)
    self.assertEqual(m["providers"]["ailab-ollama"],self.m["providers"]["ailab-ollama"])
    for k in ("defaultProvider","defaultModel","defaultThinkingLevel","retry"):self.assertEqual(s[k],self.s[k])
    self.assertEqual(s["compaction"]["reserveTokens"],32768)
    self.assertEqual(s["compaction"]["modelOverrides"]["ailab-ollama/old"],{"reserveTokens":32768})
    self.assertNotIn(v.PILOT,[x["id"] for x in m["providers"]["ailab-strata"]["models"]])
 def test_idempotence(self):
    m,s=v.evolve(self.m,self.s)
    self.assertEqual(v.evolve(m,s),(m,s))
 def test_default(self):
    m,s=v.evolve(self.m,self.s,"inkling")
    self.assertEqual((s["defaultProvider"],s["defaultModel"]),("ailab-strata","inkling-2-mini-sq-20"))
    self.assertEqual(s["defaultThinkingLevel"],"low")
 def test_unknown_refused(self):
    self.m["providers"]["ailab-strata"]["models"][0]["id"]="unexpected"
    with self.assertRaises(AssertionError):v.evolve(self.m,self.s)
if __name__=="__main__":unittest.main()
