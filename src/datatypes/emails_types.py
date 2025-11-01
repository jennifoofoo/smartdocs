# -*- coding: utf-8 -*-
"""
SmartDocs - Email Data Types

Python objects to handle EML or MSG formatted emails.

Provides:
- Email parsing and metadata extraction
- Attachment handling
- Support for both EML and MSG formats

"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr
from typing import Dict, List, Optional

import extract_msg
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from extract_msg import Attachment
from werkzeug.utils import secure_filename

from src.utilities.logger_config import logger


@dataclass
class EmailAttachment:
    """
    Dataclass which holds information about a single attachment of an email.

    It holds the following attributes:

    - parent_email as BaseEmailMessage
    - filename as str
    - secured_filename as str
    - mimetype as str
    - payload as str (base64 encoded)

    """
    parent_email: BaseEmailMessage
    filename: Optional[str] = None
    secured_filename: Optional[str] = None
    mimetype: Optional[str] = None
    payload: Optional[str] = None

    def __init__(self,
                 email_id: str,
                 attachment: EmailMessage | Attachment = None):
        super().__init__()
        self.parent_email_id = email_id
        if isinstance(attachment, EmailMessage):
            self.filename = attachment.get_filename()
            self.mimetype = attachment.get_content_type()
            self.payload = attachment.get_payload(decode=True)

        elif isinstance(attachment, Attachment):
            self.filename = attachment.longFilename or attachment.shortFilename
            self.mimetype = attachment.mimetype
            self.payload = attachment.data

        else:
            logger.error("attachment type not supported.")
            return

        if self.filename:
            self.secured_filename = secure_filename(self.filename)
        else:
            self.secured_filename = 'No_Filename_given'

    def __str__(self):
        return self.secured_filename

@dataclass
class BaseEmailMessage:
    """
    Dataclass as base class for email files (EML or MSG).

    It holds the following attributes:

    - senderName as str
    - senderAddress as str
    - receivers as List[Dict[str, str]] containing receiverName and receiverAddress
    - ccReceivers as List[Dict[str, str]] containing receiverName and receiverAddress
    - bccReceivers as List[Dict[str, str]] containing receiverName and receiverAddress
    - subject as str
    - body as str
    - sent_date as datetime.datetime
    - body as str
    - attachments as List[EmailAttachment]

    """
    senderName: Optional[str] = None
    senderAddress: Optional[str] = None
    receivers: List[Dict[str, str]] = field(default_factory=list)
    ccReceivers: List[Dict[str, str]] = field(default_factory=list)
    bccReceivers: List[Dict[str, str]] = field(default_factory=list)
    subject: Optional[str] = None
    body: str = ""
    attachments: List[EmailAttachment] = field(default_factory=list)
    sent_date: Optional[datetime] = None

    def __str__(self):
        def fmt_receivers(receivers):
            if not receivers:
                return "None"
            return ", ".join(f"{r['receiverName']} <{r['receiverAddress']}>" for r in receivers)

        def preview_text(text, limit=100):
            if not text:
                return "(empty)"
            if len(text) <= limit * 2 + 5:
                return text
            return f"{text[:limit]} ... {text[-limit:]}"
        
        attachments = []
        for att in self.attachments:
            attachments.append(str(att))
            
        lines = [
            f"Sender: {self.senderName} <{self.senderAddress}>",
            f"To: {fmt_receivers(self.receivers)}",
            f"CC: {fmt_receivers(self.ccReceivers)}",
            f"BCC: {fmt_receivers(self.bccReceivers)}",
            f"Subject: {self.subject or 'None'}",
            f"Sent date: {self.sent_date or 'None'}",
            f"Attachments: {', '.join(attachments) or 'None'}",
            "Body:", preview_text(self.body)
        ]
        return "\n".join(lines)

    def _parse_sent_date(self, file_name, raw_date) -> Optional[datetime]:
        if not raw_date:
            logger.warning(
                f"No appropriate header for sent date found in file {file_name}")
            return None
        try:
            parsed_date = dateparser.parse(raw_date)
            return parsed_date if parsed_date else None
        except Exception as e:
            logger.warning(
                f"Could not parse sent date in file {file_name}: {e}")
        return None

@dataclass
class MsgEmailMessage(BaseEmailMessage):
    """
    Parses an MSG e-mail
    """
    REC_TYPE_TO = 1
    REC_TYPE_CC = 2
    REC_TYPE_BCC = 3

    def __init__(self, file_path: str | bytes):
        super().__init__()
        try:
            msg = extract_msg.Message(file_path)

            def parse_sender(sender_str):
                match = re.match(
                    r'^(.*?)(?:\s*<([^<>]+)>)?$', sender_str.strip())
                if match:
                    return match.group(1).strip(), match.group(2) or ""
                return sender_str, ""

            sender_name, sender_email = parse_sender(msg.sender)
            self.senderName = sender_name
            self.senderAddress = sender_email

            self.receivers = [
                {'receiverName': r.name, 'receiverAddress': r.email}
                for r in msg.recipients if r.type == self.REC_TYPE_TO
            ]
            self.ccReceivers = [
                {'receiverName': r.name, 'receiverAddress': r.email}
                for r in msg.recipients if r.type == self.REC_TYPE_CC
            ]
            self.bccReceivers = [
                {'receiverName': r.name, 'receiverAddress': r.email}
                for r in msg.recipients if r.type == self.REC_TYPE_BCC
            ]

            self.subject = msg.subject
            self.sent_date = msg.date

            self.body = BeautifulSoup(
                msg.htmlBody or msg.body or "", "html.parser").get_text(separator="\n")

            for att in msg.attachments:
                attachment = EmailAttachment(email_id=self, attachment=att)
                self.attachments.append(attachment)

        except Exception as e:
            logger.error(f"Error parsing MSG: {e}")
            raise


@dataclass
class EmlEmailMessage(BaseEmailMessage):
    """
    Parses an EML e-mail
    """

    def __init__(self, email_as_bytes: bytes):
        super().__init__()
        try:
            msg = BytesParser(policy=policy.default).parsebytes(email_as_bytes)

            # Sender
            name, address = parseaddr(msg["From"])
            self.senderName = name
            self.senderAddress = address

            self.receivers = [
                {'receiverName': name, 'receiverAddress': addr}
                for name, addr in getaddresses(msg.get_all("To", [])) if addr
            ]
            self.ccReceivers = [
                {'receiverName': name, 'receiverAddress': addr}
                for name, addr in getaddresses(msg.get_all("Cc", [])) if addr
            ]
            self.bccReceivers = [
                {'receiverName': name, 'receiverAddress': addr}
                for name, addr in getaddresses(msg.get_all("Bcc", [])) if addr
            ]

            self.subject = msg.get("Subject")
            self.sent_date = super()._parse_sent_date("EML", msg.get('Date'))

            # Body
            body_parts = []
            for part in msg.walk():
                if part.get_content_type() in ["text/plain", "text/html", "text/related"]:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset()
                    decoded = payload.decode(charset, errors='replace') if charset else payload.decode(
                        'utf-8', errors='replace')
                    body_parts.append(BeautifulSoup(
                        decoded, "html.parser").get_text(separator="\n"))
            self.body = "\n".join(body_parts)

            for att in msg.iter_attachments():
                attachment = EmailAttachment(email_id=self, attachment=att)
                self.attachments.append(attachment)

        except Exception as e:
            logger.error(f"Error parsing EML: {e}")
            raise
