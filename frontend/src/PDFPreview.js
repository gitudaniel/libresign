import React, { Component } from 'react';

import './PDFPreview.css';

import qs from 'querystring';
import update from 'immutability-helper';
import { withRouter } from 'react-router';
import { Nav, NavItem, Modal, Button } from 'react-bootstrap';
import ReactLoading from 'react-loading';

import { doLinkAuthentication, doAgreeTOS } from './utils';
import PDFPages from './PDFPages';
import { SERVICE_URL } from './config';

const LOGGING_IN = 0;
const LOGGED_IN = 1;

const DOWNLOAD_FILE = 0;
const SIGN_FINISHED = 1;

class PDFPreview extends Component {
  constructor(props) {
    super(props);

    let searchparams = qs.parse(props.location.search.substr(1));

    this.state = {
      state: LOGGING_IN,
      docid: searchparams.doc,
      auth: searchparams.auth,
      token: null,
      info: null,
      show_modal: false,
    };
  }

  componentDidMount() {
    let { auth } = this.state;
    this._mounted = true;

    doLinkAuthentication(auth)
      .then(token => {
        this.setState({
          state: LOGGED_IN,
          token: token,
        });
      });
  }

  componentWillUnmount() {
    this._mounted = false;
  }

  onInfoReceived = data => {
    this.setState({
      info: data
    });
  };
  onFieldFilled = fieldid => {
    console.log(fieldid)

    this.setState(state => update(state, {
      info: {
        fields: {
          [fieldid]: {
            filled: { $set: true }
          }
        }
      }
    }))
  }

  onModalHide = () => {
    this.setState({
      modal_show: false
    })
  }

  onClickDownload = () => {
    let { docid, token } = this.state;

    let request = new XMLHttpRequest();
    request.responseType = "blob";
    request.open('GET', `${SERVICE_URL}/document/${docid}`, true);
    request.setRequestHeader('Authorization', `Bearer ${token}`);
    request.setRequestHeader('Accept', 'application/pdf');
    request.send();

    request.onreadystatechange = () => {
      if (!this._mounted) return;
      if (request.readyState === XMLHttpRequest.DONE) {
        if (request.status === 200) {
          let { info } = this.state;

          let blob = request.response;
          let url = URL.createObjectURL(blob);

          let a = document.createElement('a');
          a.download = `${info.title}.pdf`;
          a.href = url;

          document.body.appendChild(a);
          a.click()
          
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        }
      }
    };
  }

  onNavSelect = (eventKey) => {
    if (eventKey === DOWNLOAD_FILE) {
      this.onClickDownload();
    }
    else if (eventKey === SIGN_FINISHED) {
      this.onModalShow();
    }
  }

  allFieldsFilled() {
    let { info } = this.state;

    return info && info.fields.every(field => field.filled || field.optional);
  }

  onModalShow() {
    this.setState({
      modal_show: true
    })
  }

  onComplete = () => {
    let { docid, token } = this.state;

    doAgreeTOS(token, docid)
      .then(() => {
        this.props.history.push('/complete')
        console.log("here")
      })
      .catch(e => {
        console.log('failed', e);
      });
  }

  render() {
    const {
      state,
      docid,
      token,
      modal_show
    } = this.state;

    if (state === LOGGING_IN) {
      return (
        <div className="center-screen">
          <ReactLoading
            type="spokes"
            color="#000000"
            height={128}
            width={128}
          />
        </div>
      );
    }

    let all_fields_filled = this.allFieldsFilled();

    return (
      <div>
        <Nav 
          bsStyle="pills" 
          activeKey={DOWNLOAD_FILE}
          onSelect={this.onNavSelect}
        >
          <NavItem
            eventKey={DOWNLOAD_FILE}
            title="Download File"
          >
            Download File
          </NavItem>
          <NavItem
            eventKey={SIGN_FINISHED}
            title="Finished"
          >
            Finished
          </NavItem>
        </Nav>
        <br/>
        <PDFPages
          doc={docid}
          token={token}
          onInfoReceived={this.onInfoReceived}
          onFieldFilled={this.onFieldFilled}
        />

        <Modal 
          show={modal_show}
          onHide={this.onModalHide}
        >
          <Modal.Header closeButton>
            <Modal.Title>
              {
                all_fields_filled ?
                "You've signed everything" :
                "There are still some fields to sign"
              }
            </Modal.Title>
          </Modal.Header>
          <Modal.Body>
            By clicking continue you agree to our TOS.
            <br/>
            PLEASE DON'T SUE US.
          </Modal.Body>
          <Modal.Footer>
              <Button 
                onClick={this.onComplete}
                disabled={!all_fields_filled}
                bsStyle="success"
              >
                Continue
              </Button>
              <Button onClick={this.onModalHide}>Close</Button>
          </Modal.Footer>
        </Modal>
      </div>
    )
  }
}

export default withRouter(PDFPreview);

