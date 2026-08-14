# Q001 · What makes prime numbers so special?

There are infinite prime numbers—numbers that are only divisible by one and the number itself. Their existence and properties are extremely interesting to mathematicians, computer scientists, and other experts. While the entire number line—essentially every number—can be expressed as the product of prime numbers, there is great difficulty in factoring large numbers into primes. And since prime numbers have these unique properties associated with factorization, they are very useful in the field of cryptography. Imagine a computer encryption that relies on an extremely large number, such as a number with many factors of tens or even hundreds and hundreds of digits; even supercomputers will have a huge challenge in identifying its prime factors, making prime numbers especially appealing for encryption.

## Direction
Computational asymmetry between primality testing and integer factorization

Synthesize theoretical computer science literature to clarify why deterministic primality verification resides in P while exact factorization remains computationally intractable.

## Learned
- Deterministic primality verification resides in P, as proven by the AKS algorithm, without relying on unproven conjectures like the generalized Riemann hypothesis.
- AKS operates via polynomial congruence relations in quotient rings, where strategic parameter selection and modular arithmetic reduce naive exponential expansion to polynomial time.
- Theoretical tractability in P does not translate to practical efficiency; AKS is outperformed by probabilistic tests (Baillie–PSW) and certificate-generating methods (ECPP, APR).
- Worst-case complexity class membership is fundamentally distinct from the average-case hardness assumptions that govern cryptographic security.

## Evidence
- The available dataset exclusively substantiates the theoretical properties, mathematical foundations, and comparative performance metrics of the AKS primality test.
- It confirms that primality proving can be achieved deterministically in polynomial time and accurately describes the algorithmic optimizations required to avoid exponential overhead.
- It validates that asymptotic solvability guarantees do not equate to practical cryptographic utility or factorization capability.

## Limitations
- The evidence base contains zero substantive data on integer factorization algorithms, their time complexity, or formal hardness assumptions.
- Three of four source retrievals failed due to upstream extraction errors, network issues, or unsupported content types.
- The synthesis cannot establish the required computational asymmetry between primality testing and factorization.
- It cannot validate distinctions between worst-case complexity boundaries and the average-case hardness assumptions critical for cryptographic deployment.

## Open Questions
- How do sub-exponential factorization algorithms formally scale relative to polynomial primality tests across varying input sizes?
- Which specific average-case hardness assumptions currently underpin cryptographic systems, and how do they diverge from worst-case complexity proofs?
- How will evolving hardware capabilities and algorithmic refinements shift the practical thresholds for cryptographic key security?

## Next Moves
- Integrate peer-reviewed literature on integer factorization, specifically focusing on the General Number Field Sieve and sub-exponential time complexity.
- Explicitly map algorithmic classes for both primality testing and factorization to construct a valid comparative synthesis.
- Distinguish rigorously between worst-case complexity classifications and the average-case hardness assumptions required for cryptographic threat modeling.
- Evaluate which hardness assumptions align with contemporary hardware capabilities and deployment requirements for engineering teams.

## Artifacts
- Log: `logs/attempt-23e1183b540167a2b55dd9ff.log`
- Log: `logs/attempt-4f630ce9c09bff3b082f9f6f.log`
- Log: `logs/attempt-afd1c777836a532c5a0f9e89.log`
- Log: `logs/attempt-630d689f4f1a00f4e3d138d0.log`
- Log: `logs/attempt-e6e16b19020a91a7b85e4759.log`
- Log: `logs/attempt-cc97143c38b6fea6325aa8bb.log`
- Log: `logs/attempt-cbaf823178fdd867fe611d6e.log`
- Log: `logs/attempt-e2f7228b2cf229f5eb7d6667.log`

## Work Items
- `source`: completed (3 steps)
- `claim`: completed (3 steps)
- `report`: completed (3 steps)

## Review Findings
- `major` `ARGUMENT-CHAIN-BREAK`: Repair the evidentiary gap by integrating peer-reviewed literature or authoritative computational complexity resources that explicitly address integer factorization algorithms (e.g., General Number Field Sieve), their sub-exponential time complexity, and formal hardness assumptions. The current dataset exclusively covers primality testing (AKS), making the required synthesis of computational asymmetry impossible.
- `major` `ARGUMENT-CHAIN-BREAK`: Repair the evidentiary gap by integrating peer-reviewed literature or authoritative computational complexity resources that explicitly address integer factorization algorithms (e.g., General Number Field Sieve), their sub-exponential time complexity, and formal hardness assumptions. The current dataset exclusively covers primality testing (AKS), making the required synthesis of computational asymmetry impossible.
- `major` `ARGUMENT-CHAIN-BREAK`: Repair the evidentiary gap by integrating peer-reviewed literature or authoritative computational complexity resources that explicitly address integer factorization algorithms (e.g., General Number Field Sieve), their sub-exponential time complexity, and formal hardness assumptions. The current dataset exclusively covers primality testing (AKS), making the required synthesis of computational asymmetry impossible.
