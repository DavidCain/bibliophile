import React, {Component} from 'react';
import {SUPPORTED_LIBRARIES, BRANCHES} from './bibliocommons';

class WaitingOnSlowApi extends Component {
  constructor(props) {
    super(props);
    this.messages = [
      'Contacting the Goodreads API for desired books...',
      'This is going to take a little while, sorry.',
      'The Goodreads API is surpisingly slow.',
      'All other requests are parallelized, so that bit goes a tad faster.',
      <span>Although, we are still hitting a <em>lot</em> of URLs...</span>,
      'Maybe go get yourself a snack?',
      "Just kidding, we'll be done pretty soon.",
      'Most requests take about 8 seconds end-to-end.',
      "It doesn't generally take this long...",
      "Er... How are things?",
      'Hm. We really should be done by now.',
      <em>Whistle</em>,
    ];
    this.i = 0;
    this.state = {
      mesage: null,
    };

    this.advanceMessage = this.advanceMessage.bind(this);
  }

  componentDidMount() {
    this.setState({message: this.messages[0]});
    this.intervalId = setInterval(this.advanceMessage, 1500);
  }

  componentWillUnmount() {
    clearInterval(this.intervalId);
  }

  advanceMessage() {
    this.i++;

    const outOfMessages = (this.i >= this.messages.length);
    let message;
    if (outOfMessages) {
      message = this.messages[this.messages.length -1];
    } else {
      message = this.messages[this.i];
    }

    this.setState({message})
  }

  render() {
    return <p className="lead text-center">{this.state.message}</p>
  }
}

class LookupForm extends Component {
  constructor(props) {
    super(props);
    this.state = {
      userId: '41926065',
      shelf: 'to-read',
      librarySystem: 'sfpl',
      branch: 'MAIN',
    };

    this.handleSubmit = this.handleSubmit.bind(this);
    this.handleLibrarySystemChange = this.handleLibrarySystemChange.bind(this);
    this.handleInputChange = this.handleInputChange.bind(this);
  }

  async handleSubmit(event) {
    event.preventDefault();
    this.setState({fetchingBooks: true});
    await this.props.handleSubmit(this.state);
    this.setState({fetchingBooks: false});
  }

  handleInputChange(event) {
    this.setState({
      [event.target.name]: event.target.value
    });
  }

  handleLibrarySystemChange(event) {
    this.setState({
      librarySystem: event.target.value,
    });
  }

  render() {
    return (
      <form onSubmit={this.handleSubmit}>
        <div className="form-row">
          <div className="form-group col-md-6">
            <label htmlFor="goodreadsUserId">Goodreads user ID</label>
            <input className="form-control"
              id="goodreadsUserId"
              aria-describedby="idHelp"
              placeholder="41926065"
              name="userId"
              value={this.state.userId}
              onChange={this.handleInputChange}/>
            <small id="idHelp" className="form-text text-muted">
              (From the URL on your profile page,
              e.g. goodreads.com/user/show/<strong>41926065</strong>-username)
            </small>
          </div>
          <div className="form-group col-md-6">
            <label htmlFor="shelf">Goodreads shelf</label>
            <input
              className="form-control"
              id="shelf"
              aria-describedby="shelfHelp"
              name="shelf"
              value={this.state.shelf}
              onChange={this.handleInputChange}/>
            <small id="shelfHelp" className="form-text text-muted">
              Where your list of wanted books are stored.
            </small>
          </div>
        </div>


        <div className="form-row">
          <div className="form-group col-md-6">
            <label htmlFor="librarySystem">Library system</label>
            <select
              className="form-control"
              id="librarySystem"
              name="librarySystem"
              value={this.state.librarySystem}
              onChange={this.handleLibrarySystemChange}>
              {
                SUPPORTED_LIBRARIES.map((library) =>
                  <option key={library.bibliocommonsSubdomain}
                    value={library.bibliocommonsSubdomain}>
                    {library.name}
                  </option>
                )
              }
            </select>
          </div>

          <div className="form-group col-md-6">
            <label htmlFor="branch">Branch</label>
            <select
              className="form-control"
              id="branch"
              name="branch"
              value={this.state.branch}
              onChange={this.handleInputChange}>
              {
                BRANCHES[this.state.librarySystem].map((branch) =>
                  <option key={branch.name} value={branch.name}>{branch.label}</option>
                )
              }
            </select>
          </div>
        </div>

        <button type="submit" className="btn btn-primary" disabled={this.state.fetchingBooks}>
          {this.state.fetchingBooks ? 'Checking the stacks...' : 'Find books on the shelf right now'}
        </button>
        {this.state.fetchingBooks && <WaitingOnSlowApi />}
      </form>
    );
  }
}

export default LookupForm;
