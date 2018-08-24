import React, { Component } from 'react';
import update from 'immutability-helper';
import ReactLoading from 'react-loading';

import { SERVICE_URL } from './config';

import './PDFPreview.css';

class PDFPages extends Component {
  constructor(props) {
    super(props);

    this.state = {
      pages: new Array(props.pages),
      blobs: new Array(props.pages),
    }
  }

  requestImage(page, attempt) {
    let { doc, token } = this.props;

    if (!attempt) attempt = 0;

    let request = new XMLHttpRequest();
    request.responseType = "blob";
    request.onreadystatechange = () => {
      if (!this._mounted) return;
      if (request.readyState === XMLHttpRequest.DONE) {
        if (request.status !== 200)
          console.log(request);
          
        if (request.status === 200) {
          let blob = request.response;
          let url = URL.createObjectURL(blob);

          this.setState(state => {
            return update(state, {
              pages: { 
                [page]: {
                  $set: url
                }
              },
              blobs:{
                [page]: {
                  $set: blob
                }
              }
            });
          })
        }
        else if (request.status === 502) {
          setTimeout(() => {
            console.log("Redoing request")
            this.requestImage(page, attempt + 1)
          }, 10)
        }
        else {
          this.setState(state => {
            return update(state, {
              pages: { 
                [page]: {
                  $set: null
                }
              },
              blobs:{
                [page]: {
                  $set: null
                }
              }
            });
          })
        }
      }
    };
    request.open('GET', `${SERVICE_URL}/document/${doc}?page=${page+1}`, true);
    request.setRequestHeader('Authorization', `Bearer ${token}`);
    request.setRequestHeader('Accept', 'image/png');
    request.send();
  }

  componentDidMount() {
    let { pages } = this.props;
    this._mounted = true;

    for (let i = 0; i < pages; ++i) {
      setTimeout(() => {
        this.requestImage(i);
      }, 400 * i)
    }
  }

  componentWillUnmount() {
    this._mounted = false;
  }

  render() {
    let {
      pages
    } = this.state;

    let {
      fields
    } = this.props;

    return (
      <div>
        {
          pages.map((page, i) => {
            if (page === null) {
              return <div key={i}>Failed to load page</div>;
            }
            else if (!page) {
              return (
                <ReactLoading
                  type="cylon"
                  color="#000000"
                  width={64}
                  height={64}
                />
              );
            }
            else {
              return (
                <div key={i} className="page-div">
                  <img
                    src={page}
                    alt={`Agreement Page ${i}`}
                  />

                  {
                    fields ? fields[i] || null : null
                  }
                </div>
              )
            }
          })
        }
      </div>
    );
  }
}

export default PDFPages;