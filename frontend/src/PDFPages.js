import React, { Component } from 'react';

import './PDFPages.css';

import update from 'immutability-helper';
import SignaturePad from 'react-signature-pad';
import { Modal, Button, Alert } from 'react-bootstrap';
import ReactLoading from 'react-loading';

import { doLinkAuthentication, queryFieldLocations } from './utils';
import SignatureBox from './SignatureBox';
import PDFImages from './PDFImages';
import OverlayImage from './OverlayImage';
import { SERVICE_URL } from './config';

const LOADING_DOC = 1;
const LOAD_SUCCESS = 2;
const LOGIN_FAILED = 3;
const LOAD_FAILED = 4;

class PDFPages extends Component {
  constructor(props) {
    super(props);

    let {
      doc,
      token
    } = props;

    this.state = {
      state: LOADING_DOC,
      docid: doc,
      token: token,
      info: null,
      modal: {
        show: false,
        title: null,
        width: 300,
        height: 0,
        fieldid: null,
      },
      images: []
    };
  }

  componentDidMount() {
    let { token, docid } = this.state;

    queryFieldLocations(token, docid)
      .then(data => {
        let { onInfoReceived } = this.props;

        if (onInfoReceived)
          onInfoReceived(data);

        this.setState({
          info: data,
          state: LOAD_SUCCESS
        });
      })
      .catch(e => {
        this.setState({
          state: LOGIN_FAILED
        });

        throw e;
      });
  }

  onFieldClick = (aspect, index) => (e) => {
    console.log(`Field ${index} clicked`)
    this.setState(state => {
      return update(state, {
        modal: {
          show: { $set: true },
          title: { $set: "Sign Field" },
          height: { $set: state.width / aspect },
          fieldid: { $set: index },
          error: { $set: false },
        }
      })
    })
  }

  onModalHide = () => {
    this.setState(state => {
      return update(state, {
        modal: {
          show: { $set: false }
        }
      });
    });
  }

  submitSignature(field, image, token, secondTime) {
    let data = new FormData();
    data.append('fieldData', image);

    let request = new XMLHttpRequest();
    request.open('POST', `${SERVICE_URL}/field/${field}/fill-image`);
    request.setRequestHeader('Authorization', `Bearer ${token}`);
    request.send(data);

    request.onreadystatechange = () => {
      if (request.readystate === XMLHttpRequest.DONE
        && request.status === 401
        && !secondTime)
      {
        doLinkAuthentication(this.state.auth)
          .then(token => this.submitSignature(field, image, token, true))
      }
    }
  }

  onSignField = async () => {
    let { modal, token } = this.state;
    let { fieldid } = modal;

    if (this.refs.signature.isEmpty()) {
      this.setState(state => update(
        state, {
          modal: {
            error: { $set: true }
          }
        }
      ));
      return;
    }

    let field = this.state.info.fields[fieldid];
    let uri = await fetch(this.refs.signature.toDataURL());
    let image = await uri.blob();

    this.submitSignature(field.id, image, token);

    this.props.onFieldFilled(fieldid);

    this.setState(state => update(
      state, {
        modal: {
          show: { $set: false }
        },
        images: {
          $push: [{
            url: uri.url,
            field: fieldid
          }]
        },
        info: {
          fields: {
            [fieldid]: {
              filled: { $set: true }
            }
          }
        }
      }
    ));
  }

  clearSignaturePad = () => {
    this.refs.signature.clear()
  }

  render() {
    const {
      state,
      docid,
      token,
      info,
      modal,
      images,
    } = this.state;

    if (state === LOADING_DOC) {
      return <ReactLoading
        color="#000000"
        type="cylon"
      />;
    }
    if (state === LOGIN_FAILED) {
      return <div>Failed to log in, maybe you need to authenticate?</div>;
    }
    if (state === LOAD_FAILED) {
      return <div>Failed to load document, maybe check your connection?</div>;
    }

    let fieldboxes = {};
    if (LOAD_SUCCESS && info) {
      const pages = info.pages;
      const fields = info.fields;

      for (let i = 0; i < images.length; ++i) {
        let image = images[i];
        let field = fields[image.field];
        let page = field.page;
        let rect = field.rect;
        let offset = Math.ceil(pages[page].height);

        let component = (
          <OverlayImage
            width={rect.w}
            height={rect.h}
            x={rect.x}
            y={offset - rect.y - rect.h}
            src={image.url}
            key={`image-${i}`}
          />
        );

        if (!fieldboxes[field.page]) {
          fieldboxes[field.page] = []
        }

        fieldboxes[field.page].push(component);
      }
    }

    if (LOAD_SUCCESS && info) {
      const fields = info.fields;
      const pages = info.pages;
      
      for (let i = 0; i < fields.length; ++i) {
        let field = fields[i];
        let page = field.page;
        let rect = field.rect;
        let offset = Math.ceil(pages[page].height);
        let name = field.name;

        let state = (
          field.filled ? "filled" : field.optional ? "optional" : "required"
        );

        let component = (
          <SignatureBox
            x={rect.x}
            y={offset - rect.y - rect.h}
            width={rect.w}
            height={rect.h}
            key={`field-${i}`}
            title={`Sign field ${name}`}
            onClick={this.onFieldClick(rect.w / rect.h, i)}
            state={state}
          />
        );

        if (!fieldboxes[field.page]) {
          fieldboxes[field.page] = [];
        }
        
        fieldboxes[field.page].push(component);
      }
    }

    let pages_component = null;
    if (info) {
      pages_component = (
        <PDFImages
          pages={info.pages.length}
          doc={docid}
          token={token}
          fields={fieldboxes}
        />
      )
    }

    return (
      <div>
        <Modal
          show={modal.show}
        >
          <Modal.Header>
            <Modal.Title>{modal.title}</Modal.Title>
          </Modal.Header>

          <Modal.Body>
            <SignaturePad
              ref="signature"
            />
          </Modal.Body>

          {
            modal.error &&
              <Alert 
                bsStyle="danger"
                onDismiss={() => {
                  this.setState(state => update(
                    state, {
                      modal: {
                        error: { $set: false }
                      }
                    }
                  ));
                }}
              >
                You can't sign with an empty signature! 
                Please fill out a signature and try again.
              </Alert>
          }

          <Modal.Footer>
            <Button onClick={this.onSignField}>Sign</Button>
            <Button>Sign All</Button>
            <Button onClick={this.clearSignaturePad}>Clear</Button>
            <Button onClick={this.onModalHide}>Close</Button>
          </Modal.Footer>
        </Modal>
        { pages_component }
      </div>
    );
  }
}

export default PDFPages;

