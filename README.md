# Find me something to read!
[![A list of titles available at my local library][reading-list-img]][biblio]

I wrote this utility to extract the most value from two services I love dearly:

- Goodreads
- My local public library

## How I use it
Whenever I come across a title I'd like to read some day, I store it on my
Goodreads shelf. When I'd like to visit my local library branch, I visit
[biblio.dcain.me][biblio] to see which titles are available to be checked out.

## Why?
My local library branch does not have the most extensive collection. Instead of
meandering the stacks until I find a book I like, or fruitlessly querying the
catalog to see if that interesting new book is on the shelf, I'd much rather
have a script do the hard work for me.

# Can I use this?
The web interface currently supports San Francisco & Seattle, but if you live
near one of the ~190 public libraries using the BiblioCommons system, then
running this software locally should work for you. It relies on undocumented
APIs, so your mileage may vary.

You can use just the [Python backend][bibliophile-backend] locally.

# How does this work?
- The `bibliophile` Python package does the legwork of querying Goodreads &
  BiblioCommons (respectively, these are the services needed to find which
  books I'm interested in, and which books are available at the library).
- The Python module is deployed as a serverless function on AWS Lambda.
    - The function is configured with an API Gateway to enable a REST API.
    - `serverless` provides automated deployment & configuration on AWS.
- A React application provides the user interface on [biblio.dcain.me][biblio].
    - The React application is hosted as a static site on S3.
    - The static site is deployed behind CloudFront (for speed & HTTPS).

## Deployment overview
This repository contains two projects, which may be deployed separately (or together)

### Python backend (Lambda function)
1. Create an IAM user for `serverless` with permissions to create
   CloudFormation stacks, S3 buckets, Lambda functions, and more.
   Standard practice with `serverless` is to just grant the user an
   administrator policy, though this is not ideal security.
2. Create access keys for this user, then run:
   ```
   SLS_DEBUG=* ./node_modules/serverless/bin/serverless deploy
   ```

Configuration for `serverless deploy` is contained in `serverless.yml`.
If you want to deploy this service to your own domain, you'll need to
tweak settings in there (namely, changing domain names).

### React frontend (user interface at biblio.dcain.me)
See [README.md][react-frontend-readme] for more information.


[bibliophile-backend]: https://github.com/DavidCain/bibliophile-backend
[react-frontend-readme]: react-frontend/README.md
[reading-list-img]: screenshots/reading_list.png
[biblio]: https://biblio.dcain.me
