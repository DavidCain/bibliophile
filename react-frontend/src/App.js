import React, {Component} from 'react';

import axios from 'axios';

//import './App.css';  // unused!
import LookupForm from './LookupForm';
import BookList from './BookList';

const API_URL = 'https://api.dcain.me/findBooks';

class App extends Component { constructor(props) {
    super(props);
    this.state = {
      userId: '41926065',
      availableBooks: null,
    };

    this.fetchReadingList = this.fetchReadingList.bind(this);
  }

  async fetchReadingList(options) {
    this.setState({availableBooks: null});

    const params = {
      userId: options.userId,
      shelf: options.shelf,
      biblio: options.librarySystem,
      branch: options.branch,
    };
    const response = await axios.post(API_URL, params);
    this.setState({availableBooks: response.data.books});
  }

  render() {
    return (
      <div>
        <h1>Find great books</h1>
        <LookupForm handleSubmit={this.fetchReadingList} />
        {this.state.availableBooks && <BookList books={this.state.availableBooks}/>}
      </div>
    );
  }
}

export default App;
