import email, imaplib
import datetime


def login(logfile):
	"""
	Log into both accounts
	"""
	
	# Credentials for old account
	host_oldEmail = <IMAP_SERVER>
	username_oldEmail = <YOUR_USERNAME>
	password_oldEmail = <YOUR_PASSWORD>
	# Credentials for new account
	host_newEmail = <IMAP_SERVER>
	username_newEmail = <YOUR_USERNAME>
	password_newEmail = <YOUR_PASSWORD>

	oldEmail = imaplib.IMAP4_SSL(host_oldEmail)
	oldEmail.login(username_oldEmail, password_oldEmail)
	oldEmail_folders = oldEmail.list()
	logfile.write("\nLogged in oldEmail")

	newEmail = imaplib.IMAP4_SSL(host_newEmail)
	newEmail.login(username_newEmail, password_newEmail)
	logfile.write("\nLogged in newEmail")

	if oldEmail_folders[0]!="OK":
		print("ERROR: oldEmail folders not obtained")
		logfile.write("\nERROR: oldEmail folders not obtained")
		sys.exit(0)
	
	return oldEmail, newEmail, oldEmail_folders, logfile


def logout(oldEmail, newEmail, logfile):
	"""
	Log out of both accounts
	"""
	oldEmail.logout()
	logfile.write("\nLogged out oldEmail")
	newEmail.logout()
	logfile.write("\nLogged out newEmail")
	logfile.close()


def compare_count(oldEmail, newEmail, oldEmail_folders, logfile):
	"""
	Compare folders in both accounts for checking
	"""
	logfile.write("\nCurrent Folder Count:")
	for fname in oldEmail_folders:
		status, data = oldEmail.select('\"' + fname + '\"')
		statusg, datag = newEmail.select('\"' + fname + '\"')
		if statusg != 'OK': # Folder has not been created in newEmail yet
			datag = [0]
		if int(data[0])!=int(datag[0]):
			logfile.write("\nMailbox: {} || oldEmail count: {} || newEmail count: {}".format(fname, int(data[0]), int(datag[0])))


def process_email(oldEmail, newEmail, fname, logfile):
	"""
	Process single mailbox/folder/label
	"""
	try:
		rv, data = oldEmail.search(None, "ALL")
		if rv != 'OK' or data == [b'']:
			logfile.write("\nEmpty oldEmail folder!")
			return
		rvg, datag = newEmail.search(None, "ALL")
		if rvg != 'OK' or datag == [b'']:
			logfile.write("\nEmpty newEmail folder!")

	except imaplib.IMAP4.abort as e:
		oldEmail, newEmail, oldEmail_folders, logfile = login(logfile)
		status, data = oldEmail.select('\"' + fname + '\"')
		rv, data = oldEmail.search(None, "ALL")
		statusg, datag = newEmail.select('\"' + fname + '\"')
		rvg, datag = newEmail.search(None, "ALL")


	num_emails = len(data[0].split())
	for num in data[0].split():
		logfile.write("Fetching email from oldEmail @ num="+str(int(num)))
		try:
			rv, data = oldEmail.fetch(num, '(RFC822)')
			if rv != 'OK':
				print("Error in getting message "+str(int(num)))
				logfile.write("\nERROR: in getting message "+str(int(num)))
				continue

		except imaplib.IMAP4.abort as e:
			oldEmail, newEmail, oldEmail_folders, logfile = login(logfile)
			status, data = oldEmail.select('\"' + fname + '\"')
			rv, data = oldEmail.search(None, "ALL")
			rv, data = oldEmail.fetch(num, '(RFC822)')

		logfile.write("Email fetched! Appending to newEmail...")
		msg = data[0][1]
		email_msg = email.message_from_bytes(msg)
		if email_msg['date'] in [None, "", " "]:
			org_date = email.utils.mktime_tz(email.utils.parsedate_tz(email_msg['received'].split(';')[-1]))
		else:
			org_date = email.utils.mktime_tz(email.utils.parsedate_tz(email_msg['date']))

		try:
			rvg, datag = newEmail.append('\"' + fname + '\"', None, imaplib.Time2Internaldate(org_date), msg)
			if rvg != 'OK':
				print("Error in adding message "+str(int(num)))
				logfile.write("\nERROR: in adding message "+str(int(num)))
				continue

		except imaplib.IMAP4.abort as e:
			oldEmail, newEmail, oldEmail_folders, logfile = login(logfile)
			statusg, datag = newEmail.select('\"' + fname + '\"')
			rvg, datag = newEmail.search(None, "ALL")
			rvg, datag = newEmail.append('\"' + fname + '\"', None, imaplib.Time2Internaldate(org_date), msg)	

		logfile.write("\nProcessed # "+str(int(num))+" of "+str(num_emails))


def process_all(oldEmail, newEmail, oldEmail_folders, logfile):
	"""
	Process all mailboxes/folders/labels
	"""
	folder_names = []
	excluded = ["Archive", "Draft", "Inbox", "Sent", "Trash"] # General folders that are set up automatically when user sets up forwarding
	
	for folder in oldEmail_folders[1:]:
		for f in folder:
			fname = str(f).split('"')[-2]
			if fname not in excluded:
				folder_names.append(fname)
	compare_count(oldEmail, newEmail, folder_names, logfile) # Folder count before processing

	for fname in folder_names:
		logfile.write("\n---NOW PROCESSING FOLDER "+fname+"---")
		try:
			status, data = oldEmail.select('\"' + fname + '\"')
			if status != "OK":
				print("Error! Skipped "+fname)
				logfile.write("\nERROR: Skipped "+fname)
				continue
			statusg, datag = newEmail.select('\"' + fname + '\"')
		except imaplib.IMAP4.abort as e: 
			# Reconnect to handle periodic socket close
			oldEmail, newEmail, oldEmail_folders, logfile = login(logfile)
			status, data = oldEmail.select('\"' + fname + '\"')
			statusg, datag = newEmail.select('\"' + fname + '\"')

		logfile.write("\nMailbox: {} || No of items in old mailbox: {}".format(fname,data))
		if statusg != 'OK':
			logfile.write("\nCreating new mailbox...")
			try:
				newEmail.create('\"' + fname + '\"')
				statusg, datag = newEmail.select('\"' + fname + '\"')
			except imaplib.IMAP4.abort as e:
				oldEmail, newEmail, oldEmail_folders, logfile = login(logfile)
				newEmail.create('\"' + fname + '\"')
				statusg, datag = newEmail.select('\"' + fname + '\"')

		process_email(oldEmail, newEmail, fname, logfile)
	return folder_names


def main():

	logfile = open("email_log.txt", "a")
	oldEmail, newEmail, oldEmail_folders, logfile = login(logfile)
	oldEmail_folder_names = process_all(oldEmail, newEmail, oldEmail_folders, logfile)
	compare_count(oldEmail, newEmail, oldEmail_folder_names, logfile) # Folder count after processing
	logout(oldEmail, newEmail, logfile)


if __name__ == '__main__':
	main()
