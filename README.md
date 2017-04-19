# Find me something to read!
I wrote this utility to extract the most value from two services I love dearly:

- Goodreads
- The Seattle Public Library system

## How I use it
Whenever I come across a title I'd like to read some day, I store it on my
Goodreads shelf. When I'd like to visit my local library branch, I run this
script, and it will tell me which titles are available to be checked out.

## Why?
I live in a wonderfully tech-oriented city. Our libraries have blazing-fast
internet access and the entire catalog is accessible via a public API. However,
my local library branch does not have the most extensive collection. Instead of
meandering the stacks until I find a book I like, or fruitlessly querying the
catalog to see if that interesting new book is on the shelf, I'd much rather
have a script do the hard work for me.

# Can I use this?
If you live near one of the ~190 public libraries using the BiblioCommons
system, then this software should work for you. It relies on undocumented
APIs, so your mileage may vary.

1. Apply for a [Goodreads Developer Key][goodreads-api].
2. Obtain your Goodreads user id
3. [Optional] Set both these values in your `.bashrc`

    ```sh
    export GOODREADS_USER_ID=123456789
    export GOODREADS_DEV_KEY=whatever-your-actual-key-is
    ```
4. Run the script!

    ```sh
    ./lookup.py --biblio seattle  # Set to your own city!
    ```

Make sure you adhere to the terms of [Goodreads' API][goodreads-api-terms], and
have fun.

## Other options
You can choose to show only titles available at your local branch, select titles
from another Goodreads shelf, etc. Pass `--help` to see all options:

```
usage: lookup.py [-h] [--branch BRANCH] [--shelf SHELF] [--biblio BIBLIO]
                 [--csv CSV]
                 [user_id] [dev_key]

See which books you want to read are available at your local library.

positional arguments:
  user_id          User's ID on Goodreads
  dev_key          Goodreads developer key. See https://www.goodreads.com/api

optional arguments:
  -h, --help       show this help message and exit
  --branch BRANCH  Only show titles available at this branch. e.g. 'Fremont
                   Branch'
  --shelf SHELF    Name of the shelf containing desired books
  --biblio BIBLIO  subdomain of bibliocommons.com (seattle, vpl, etc.)
  --csv CSV        Output results to a CSV of this name.
```


[goodreads-api]: https://www.goodreads.com/api
[goodreads-api-terms]: https://www.goodreads.com/api/terms
