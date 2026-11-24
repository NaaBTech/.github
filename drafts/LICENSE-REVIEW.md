# The license of the defaults repository: a factual review

**Status: a review for the organization owners. The license that is already in place is not changed by this document.**

## What is in the repository

| Content | Origin | License |
| --- | --- | --- |
| The organization defaults, the documentation and the workflow | written for NaaB Tech | the repository license |
| The two vendored JSON Schemas | taken from SchemaStore | Apache-2.0, with the upstream notice |
| The Apache-2.0 license text and the notice | taken from SchemaStore | Apache-2.0 |
| The validation and refresh scripts | written for NaaB Tech | the repository license |

The vendored material carries its own license, which is the same one, so there is no conflict to resolve. The upstream notice is reproduced unchanged, as section 4(d) requires, and the provenance record ties every vendored file to its source and its hash.

## What Apache-2.0 permits

- Commercial and non-commercial use, including in proprietary products.
- Modification and distribution, including in closed-source software.
- Private use and internal deployment.
- Patent use, with an express grant that covers the contributors' contributions.

## What it requires

- The license and the copyright notice travel with any distribution.
- Modified files carry a prominent notice.
- The upstream notice travels with the vendored material.
- The patent grant ends if a patent suit is brought against the contributors.

## The points that need a qualified review

1. **The intended publication model.** The repository holds the defaults that other repositories inherit. Apache-2.0 is permissive, so a company repository can adopt these defaults and adapt them without becoming a derivative work. If the intention were the opposite, the license would have to change, and so would the contribution model.

2. **Contributor ownership.** Outside contributions carry the copyright of their authors unless a contributor agreement or a developer certificate of origin is in place. The repository has neither a Developer Certificate of Origin (`Signed-off-by`) requirement nor a contributor agreement. Under a permissive license this is low risk, but it is an open point.

3. **Trademarks.** Apache-2.0 does not grant trademark rights. The brand name and the product prefix are used as names, not as a trademark licence. If the organization wants to protect the brand, that is a separate registration, and the wording of the documentation should stay descriptive.

4. **Third-party assets.** The vendored schemas are covered. Any future asset that is not covered by the repository license needs its own attribution recorded in the provenance file before it is committed.

5. **The organization profile and the public repositories.** They are the public face of the organization. The repository license covers the files, not the presentation of the brand.

## The recommendation

Apache-2.0 fits the intended model: the defaults are meant to be adopted and adapted by repositories that are not open source, and a copyleft license would place conditions on that adoption. The review that is still missing is the legal one: a qualified reviewer should confirm the contributor-ownership point and the trademark point before the license is treated as settled.
