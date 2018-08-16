import React, {Component} from 'react';


class Book extends Component {
  render() {
    const book = this.props;

    return (
      <div className="media my-4">
        <a href={ book.full_record_link }>
          <img
            height="200"
            className="d-none d-md-block align-self-start mr-3"
            src={ book.cover_image }
            alt={`Cover of ${book.title} by ${book.author}`} />
        </a>
        <div className="media-body">
          <h3 className="mt-0 mb-1">
            <span>{ book.title }</span>
            <a href={ book.full_record_link }>
              <span className="badge badge-info float-right">{ book.call_number }</span>
            </a>
          </h3>
          <h5 className="text-muted">{ book.author }</h5>
          <p>
            <a href={ book.full_record_link }>
              <img
                height="200"
                className="d-block d-md-none float-left mb-3 mr-3"
                src={ book.cover_image }
                alt={`Cover of ${book.title} by ${book.author}`} />
            </a>
            { book.description }
          </p>
        </div>
      </div>
    );
  }
}


class BookList extends Component {
  render() {
    // Null books means that we're still querying
    if (!this.props.books) {
      return null;
    }

    return (
      <div>
        <hr />
        <h1 className="text-center">Reading List</h1>
        <ul className="list-unstyled">
          {this.props.books.map((book) =>
            <li key={book.call_number}>
              <Book
                title={book.title}
                author={book.author}
                description={book.description}
                cover_image={book.cover_image}
                full_record_link={book.full_record_link}
                call_number={book.call_number} />
            </li>
          )}
        </ul>
        {(this.props.books.length === 0) &&
            <div className="alert alert-info">Nothing found on the shelf.</div>
        }
      </div>
    );
  }
}

export default BookList;
