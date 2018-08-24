import React, { Component } from 'react';

import './SignatureBox.css';

class SignatureBox extends Component {
  render() {
    let {
      width,
      height,
      x,
      y,
      filled,
      title,
      onClick,
      state
    } = this.props;

    var colour;
    if (state === "filled")
      colour = "lime";
    else if (state === "optional")
      colour = "orange";
    else 
      colour = "red";

    return (
      <button
        className='signature-box'
        style={{
          width: width,
          height: height,
          top: y,
          left: x,
          border: `solid ${colour}`,
        }}
        title={title}
        onClick={onClick}
        aria-label={title}
      >
        { !filled && "*" }
      </button>
    );
  }
}

export default SignatureBox;
