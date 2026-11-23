import itertools, math, unittest
import numpy as np
import study as s

def reference(x,y,r):
    n=len(x);d=np.full((n+1,n+1),np.inf);d[0,0]=0
    for i in range(1,n+1):
        for j in range(max(1,i-r),min(n,i+r)+1):
            d[i,j]=sum((x[i-1]-y[j-1])**2)+min(d[i-1,j],d[i,j-1],d[i-1,j-1])
    return d[n,n]

class StudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.distance=staticmethod(s.backend())

    def test_compiled_backend_matches_independent_reference(self):
        rng=np.random.default_rng(37)
        for n in range(2,10):
            for r in range(n):
                for dims in (1,3):
                    x=rng.normal(size=(n,dims));y=rng.normal(size=(n,dims))
                    expected=reference(x,y,r);actual,_=self.distance(x,y,radius=r)
                    self.assertAlmostEqual(actual,expected,places=10)
                    cutoff=expected*.5
                    value,_=self.distance(x,y,cutoff,radius=r)
                    self.assertTrue(math.isinf(value) or value>=expected-1e-10)

    def test_two_pass_bound_exhaustive_small_alphabet(self):
        # Test the nontrivial second projection pass independently of search.
        words=np.array(list(itertools.product([-1.,0.,1.],repeat=4)))[:,:,None]
        for r in range(4):
            env=s.envelope(words,r)
            for query in words:
                projected=np.clip(query,*env)
                first=((query-projected)**2).sum(axis=(1,2))
                plo,phi=s.envelope(projected,r)
                lb=first+((words-np.clip(words,plo,phi))**2).sum(axis=(1,2))
                truth=np.array([self.distance(query,c,radius=r)[0] for c in words])
                self.assertTrue(np.all(lb<=truth+1e-10))

    def test_multivariate_bound_under_coupled_warping(self):
        rng=np.random.default_rng(287)
        candidates=rng.normal(size=(40,s.N,3));env=s.envelope(candidates)
        for _ in range(30):
            q=rng.normal(size=(s.N,3));lb,k=s.bounds(q,candidates,env)
            truth=np.array([self.distance(q,c)[0] for c in candidates])
            self.assertTrue(np.all(lb<=truth+1e-9))
            self.assertTrue(np.all(lb>=k-1e-9))

    def test_exact_search_duplicates_and_adversarial_order(self):
        rng=np.random.default_rng(23)
        candidates=rng.normal(size=(40,s.N,3));candidates[2]=candidates[3]
        env=s.envelope(candidates);features=s.summaries(candidates)
        queries=[candidates[2],np.zeros((s.N,3)),rng.normal(size=(s.N,3))]
        for q in queries:
            oracle=s.search(q,candidates,env,features,self.distance,'exhaustive')
            for method in s.METHODS[1:]:
                actual=s.search(q,candidates,env,features,self.distance,method,weight=100)
                self.assertEqual(actual['winner'],oracle['winner'])
                self.assertAlmostEqual(actual['distance'],oracle['distance'])

if __name__=='__main__':unittest.main()
