import React, { Component } from 'react';
import './App.css';

import { BrowserRouter as Router, Route } from 'react-router-dom';

import PDFJS from 'pdfjs-dist';

import PDFPreview from './PDFPreview';
import FillForm from './Signature';
import AllDone from './AllDone';

window.PDFJS = PDFJS;

class App extends Component {
  render() {
    return (
      <Router>
        <div>
          <Route
            exact path='/view'
            component={() => <PDFPreview/>}
          />
          <Route
            exact path='/sign'
            component={() => <FillForm/>}
          />
          <Route
            exact path='/complete'
            component={() => <AllDone/>}
          />
        </div>
      </Router>
    );
  }
}

export default App;
