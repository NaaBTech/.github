# The launch of the main website: what has to change

**Status: a checklist for the launch. The coming soon page is not replaced by this document.**

## The situation

`naabtech.ir` currently serves the coming soon page. When the new website is ready to launch, the website repository, organization profile, and repository metadata are updated to reflect the release.

## Before the launch

1. **Publish the new website** to the repository that will serve it, and decide what happens to the coming soon page: it either becomes the landing page for the new site, or it is archived with a note that explains why.
2. **Update the repository descriptions and the topics** so that they describe what the repository holds after the launch.
3. **Update the profile** for the live website launch. The baseline copy from [ORGANIZATION-PROFILE-DRAFT.md](ORGANIZATION-PROFILE-DRAFT.md) has already been published to `profile/README.md`; review it against the launched site and update links or product descriptions as needed.
4. **Update the homepage field** of the repository that serves the site. It currently points at `naabtech.ir`, which stays correct only while the coming soon page is the one that is served.
5. **Check the contact channels.** Every channel in the published channels table has to be one that the organization actually monitors before it is published, and the security mailbox has to exist and be staffed before it is named anywhere.
6. **Check the security policy.** The reporting route in it has to be the route that is actually monitored.

## After the launch

1. **Re-run the link check.** The website and the published profile carry links to `naabtech.ir`. A link check in continuous integration covers the repositories; the profile page is not covered by it.
2. **Update the onboarding checklist** so that it describes the repositories that exist after the launch.
