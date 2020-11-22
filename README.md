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

The [web interface][biblio] currently supports Alameda County, San Francisco,
and Seattle, but if you live near one of the ~190 public libraries using the
BiblioCommons system, then running this software locally should work for you.
It relies on undocumented APIs, so your mileage may vary.

You can also use just the [Python backend][bibliophile-backend] locally.

# How does this work?

- The [`bibliophile` Python package][bibliophile-backend] does the legwork of
  querying Goodreads & BiblioCommons (respectively, these are the services
  needed to find which books I'm interested in, and which books are available
  at the library).
- This repository defines some Lambda functions that are deployed to public
  endpoints, accessible at api.dcain.me
  - Function are configured with an API Gateway to enable a REST API.
  - `serverless` provides automated deployment & configuration on AWS.
- A [web app][bibliophile-frontend] provides the user interface on [biblio.dcain.me][biblio].

## Deploying AWS Lambda functions

1. [Download Docker][docker].
   We choose to Dockerize the pip environment because both `grequests` and
   `lxml` (dependencies of `bibliophile`) are C-based, and need to compile
   binaries for use on the Lambda VM. By using Docker, we can make use of an
   image that mirrors exactly what AWS will run in Lambda-land.
2. Create an IAM user for `serverless` with permissions to create
   CloudFormation stacks, S3 buckets, Lambda functions, and more.
   Standard practice with `serverless` is to just grant the user an
   administrator policy, though this is not ideal security.
3. Create access keys for the `serverless` user
4. (one-time) create the `customDomain` that the API will be served on:
   ```
   npm run serverless create_domain
   ```
   (Note that new domains may take up to 40 minutes to initialize)
5. Deploy the latest version of the endpoint:
   ```
   npm run deploy
   ```

Once the above is done, a simple end-to-end test:

```
curl -X POST 'https://api.dcain.me/bibliophile/read_shelf' \
    --header "Content-Type: application/json" \
    --data '{"userId": "41926065", "shelf": "to-read"}'
```

### Customization

Configuration for `serverless deploy` is contained in `serverless.yml`.
If you want to deploy this service to your own domain, you'll need to
tweak settings in there (namely, changing domain names).

# TODO

This is a pet project I work on whenever I'm so inclined.

Accordingly, there are a lot of TODOs at any given moment...

## Support shelves with over 200 books

Right now, this tool only reads the first 200 books on the `to-read` shelf
(the Goodreads API prevents reading more). To support larger shelves, we should
call the API endpoint a few times (while not breaking the "1 query per second" rule
Goodreads has on API integrations.

## Batch catalog queries

After we've fetched the Goodreads shelf, we could make catalog queries, say, 20 books at a time.
The backend already parallelizes execution of large searches, but this would allow us to have
more iterative results which appear on-screen as data is available.

## Search for similar ISBNs

Currently, the search algorithm prefers an exact match on ISBN. This results in fewer
results than you'd expect, since popular titles are generally released with several ISBNs
(for example, paperback and hardcover editions get different ISBNs).

### Why not a search by author & title?

For famous authors/works, the number of incorrect results are just too numerous.
Even when limiting to books (to exclude all the matching DVDs and audio recordings),
other results appear alongside the "real" result.

### Prefer first ISBN, but allow others

An excellent way around this problem is to utilize Goodreads "other editions" feature:

1. For each book, see if there's an exact match in the catalog. If so? Great, we're done.
2. If there's no match, check for other editions' ISBNs. If no other editions, exit.
3. Search by title & author, and accept any results which have a known ISBN.

An endpoint exists to do this (`work.editions`), though it requires special permission.
I'm waiting to hear back from Goodreads staff.

[bibliophile-backend]: https://github.com/DavidCain/bibliophile-backend
[bibliophile-frontend]: https://github.com/DavidCain/bibliophile-frontend
[docker]: https://www.docker.com/products/docker-desktop
[reading-list-img]: screenshots/reading_list.png
[biblio]: https://biblio.dcain.me
