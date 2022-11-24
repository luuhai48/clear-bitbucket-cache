# Use case

When create a pull request, my pipeline need to go through multiple steps, like `lint`, `format`, then `build`.
I don't want my cache to be cleared at every step, so this will help.

# How to use:

Add to your `bitbucket-pipelines.yml` file:

```yaml
definitions:
  caches:
    cache_checksum: .cache_checksum

  steps:
    - step: &delete-cache
        name: delete cache if changes in the build dependencies
        caches:
          - cache_checksum
        script:
          - pipe: luuhai48/clear-bitbucket-cache:latest
            variables:
              BITBUCKET_USERNAME: $USERNAME
              BITBUCKET_APP_PASSWORD: $APP_PASSWORD
              CACHES: ["node"]
              CHECKSUM_FILES: ["package.json"]
              # DEBUG: "<boolean>" # Optional
              # WORKSPACE: "<string>" # Optional
              # REPO_SLUG: "<string>" # Optional
        condition:
          changesets:
            includePaths:
              - package.json
...
pipelines:
  pull-requests:
    '**':
      - step: *delete-cache
      - step: *ci-check

  branches:
    dev:
      - step: *delete-cache
      - step: *deploy
```

Other variables, please refer to document: https://bitbucket.org/atlassian/bitbucket-clear-cache/src/master/README.md
